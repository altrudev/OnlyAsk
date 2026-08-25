use rig::agent::{AgentHook, HookContext, InvalidToolCallAction, ToolCall, ToolCallAction};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum DecisionKind {
    Allow,
    Escalate,
    Deny,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct Permission {
    pub resource: String,
    pub action: String,
}

impl Permission {
    pub fn matches(&self, resource: &str, action: &str) -> bool {
        let resource_match = if self.resource == "*" {
            true
        } else if let Some(prefix) = self.resource.strip_suffix("/*") {
            resource.starts_with(&format!("{prefix}/"))
        } else {
            self.resource == resource
        };
        let action_match = self.action == "*" || self.action == action;
        resource_match && action_match
    }
}

#[derive(Clone, Debug)]
pub enum ResourceResolver {
    Fixed(String),
    StringField { prefix: String, field: String },
}

impl ResourceResolver {
    pub fn resolve(&self, args: &Value) -> Result<String, String> {
        let resource = match self {
            Self::Fixed(resource) => resource.clone(),
            Self::StringField { prefix, field } => {
                let value = args
                    .get(field)
                    .and_then(Value::as_str)
                    .ok_or_else(|| format!("missing string field: {field}"))?;
                format!("{prefix}{value}")
            }
        };
        if resource.trim().is_empty() {
            return Err("empty authority resource".to_string());
        }
        Ok(resource)
    }
}

#[derive(Clone, Debug)]
pub struct RigToolPolicy {
    pub resource: ResourceResolver,
    pub operation: String,
    pub mutating: bool,
    pub transactional: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Decision {
    pub kind: DecisionKind,
    pub reason: String,
    pub authority_basis: Option<String>,
    pub resource: Option<String>,
    pub operation: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct Evidence {
    pub runtime: &'static str,
    pub tool: String,
    pub decision: DecisionKind,
    pub reason: String,
    pub authority_basis: Option<String>,
    pub resource: Option<String>,
    pub operation: Option<String>,
}

#[derive(Clone)]
pub struct OnlyAskRigGate {
    allow: Vec<Permission>,
    deny: Vec<Permission>,
    policies: HashMap<String, RigToolPolicy>,
    evidence: Arc<Mutex<Vec<Evidence>>>,
}

impl OnlyAskRigGate {
    pub fn new(
        allow: Vec<Permission>,
        deny: Vec<Permission>,
        policies: HashMap<String, RigToolPolicy>,
    ) -> Self {
        Self {
            allow,
            deny,
            policies,
            evidence: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn decide(&self, tool_name: &str, args: &Value) -> Decision {
        let decision = self.decide_inner(tool_name, args);
        if let Ok(mut evidence) = self.evidence.lock() {
            evidence.push(Evidence {
                runtime: "rig",
                tool: tool_name.to_string(),
                decision: decision.kind,
                reason: decision.reason.clone(),
                authority_basis: decision.authority_basis.clone(),
                resource: decision.resource.clone(),
                operation: decision.operation.clone(),
            });
        }
        decision
    }

    pub fn evidence(&self) -> Vec<Evidence> {
        self.evidence
            .lock()
            .map(|entries| entries.clone())
            .unwrap_or_default()
    }

    fn decide_inner(&self, tool_name: &str, args: &Value) -> Decision {
        let Some(policy) = self.policies.get(tool_name) else {
            return Decision {
                kind: DecisionKind::Deny,
                reason: "Tool is not registered in the capability surface.".to_string(),
                authority_basis: Some("runtime:unregistered_tool".to_string()),
                resource: None,
                operation: None,
            };
        };

        let resource = match policy.resource.resolve(args) {
            Ok(resource) => resource,
            Err(_) => {
                return Decision {
                    kind: DecisionKind::Deny,
                    reason: "Tool input could not be mapped to authority.".to_string(),
                    authority_basis: Some("runtime:invalid_authority_mapping".to_string()),
                    resource: None,
                    operation: Some(policy.operation.clone()),
                };
            }
        };

        if policy.mutating && !policy.transactional {
            return Decision {
                kind: DecisionKind::Deny,
                reason: "Mutating tool lacks transactional enforcement.".to_string(),
                authority_basis: Some("runtime:transaction_required".to_string()),
                resource: Some(resource),
                operation: Some(policy.operation.clone()),
            };
        }

        if let Some(permission) = self
            .deny
            .iter()
            .find(|permission| permission.matches(&resource, &policy.operation))
        {
            return Decision {
                kind: DecisionKind::Deny,
                reason: "Action conflicts with an explicit prohibition.".to_string(),
                authority_basis: Some(format!(
                    "deny:{}:{}",
                    permission.resource, permission.action
                )),
                resource: Some(resource),
                operation: Some(policy.operation.clone()),
            };
        }

        if let Some(permission) = self
            .allow
            .iter()
            .find(|permission| permission.matches(&resource, &policy.operation))
        {
            return Decision {
                kind: DecisionKind::Allow,
                reason: "Action falls inside delegated authority.".to_string(),
                authority_basis: Some(format!(
                    "allow:{}:{}",
                    permission.resource, permission.action
                )),
                resource: Some(resource),
                operation: Some(policy.operation.clone()),
            };
        }

        Decision {
            kind: DecisionKind::Escalate,
            reason: "No delegated permission covers this action.".to_string(),
            authority_basis: None,
            resource: Some(resource),
            operation: Some(policy.operation.clone()),
        }
    }
}

#[derive(Clone)]
pub struct OnlyAskRigHook {
    gate: OnlyAskRigGate,
}

impl OnlyAskRigHook {
    pub fn new(gate: OnlyAskRigGate) -> Self {
        Self { gate }
    }

    pub fn gate(&self) -> &OnlyAskRigGate {
        &self.gate
    }
}

impl AgentHook for OnlyAskRigHook {
    async fn on_tool_call(&self, _ctx: &HookContext, event: ToolCall<'_>) -> ToolCallAction {
        let args = serde_json::from_str::<Value>(event.args).unwrap_or(Value::Null);
        let decision = self.gate.decide(event.tool_name, &args);
        match decision.kind {
            DecisionKind::Allow => ToolCallAction::run(),
            DecisionKind::Escalate => ToolCallAction::skip(format!(
                "OnlyAsk escalate: {}",
                decision.reason
            )),
            DecisionKind::Deny => ToolCallAction::skip(format!(
                "OnlyAsk deny: {}",
                decision.reason
            )),
        }
    }

    async fn on_invalid_tool_call(
        &self,
        _ctx: &HookContext,
        _event: &rig::agent::InvalidToolCallContext,
    ) -> Option<InvalidToolCallAction> {
        Some(InvalidToolCallAction::skip(
            "OnlyAsk denied an invalid or unregistered tool call.",
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Deserialize)]
    struct Fixture {
        allow: Vec<Permission>,
        deny: Vec<Permission>,
        cases: Vec<FixtureCase>,
    }

    #[derive(Deserialize)]
    struct FixtureCase {
        name: String,
        tool: String,
        resource: Option<String>,
        operation: Option<String>,
        mutating: Option<bool>,
        transactional: Option<bool>,
        registered: Option<bool>,
        params: Value,
        expected: DecisionKind,
    }

    fn fixture() -> Fixture {
        serde_json::from_str(include_str!(
            "../../../conformance/runtime_adapter_cases.json"
        ))
        .expect("shared conformance fixture must parse")
    }

    fn gate_from_fixture(fixture: &Fixture) -> OnlyAskRigGate {
        let mut policies = HashMap::new();
        for case in &fixture.cases {
            if case.registered == Some(false) {
                continue;
            }
            let resource = case.resource.clone().unwrap_or_default();
            policies.insert(
                case.tool.clone(),
                RigToolPolicy {
                    resource: ResourceResolver::Fixed(resource),
                    operation: case.operation.clone().unwrap_or_else(|| "read".to_string()),
                    mutating: case.mutating.unwrap_or(false),
                    transactional: case.transactional.unwrap_or(false),
                },
            );
        }
        OnlyAskRigGate::new(fixture.allow.clone(), fixture.deny.clone(), policies)
    }

    #[test]
    fn shared_conformance_fixture_matches_python_contract() {
        let fixture = fixture();
        let gate = gate_from_fixture(&fixture);
        for case in &fixture.cases {
            let decision = gate.decide(&case.tool, &case.params);
            assert_eq!(decision.kind, case.expected, "{}", case.name);
        }
        assert_eq!(gate.evidence().len(), fixture.cases.len());
    }

    #[test]
    fn unregistered_tool_stays_denied_even_with_wildcard_allow() {
        let gate = OnlyAskRigGate::new(
            vec![Permission {
                resource: "*".to_string(),
                action: "*".to_string(),
            }],
            vec![],
            HashMap::new(),
        );
        let decision = gate.decide("shell", &serde_json::json!({"command": "echo no"}));
        assert_eq!(decision.kind, DecisionKind::Deny);
        assert_eq!(
            decision.authority_basis.as_deref(),
            Some("runtime:unregistered_tool")
        );
    }

    #[test]
    fn string_field_resource_resolver_is_typed_and_fail_closed() {
        let resolver = ResourceResolver::StringField {
            prefix: "github/".to_string(),
            field: "repo".to_string(),
        };
        assert_eq!(
            resolver.resolve(&serde_json::json!({"repo": "altrudev/OnlyAsk"})),
            Ok("github/altrudev/OnlyAsk".to_string())
        );
        assert!(resolver.resolve(&serde_json::json!({})).is_err());
    }
}
