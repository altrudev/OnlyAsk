from onlyask.product import OnlyAskProductSession
from onlyask.webapp import OnlyAskConsole


def test_routine_repair_runs_without_human_ask():
    session = OnlyAskProductSession()

    inspected = session.inspect_homepage()
    repaired = session.repair_contact_link()

    assert inspected.state.value == "verified"
    assert repaired.state.value == "verified"
    assert session.ask_count == 0
    assert 'href="/contact"' in session.workspace.homepage_html
    assert session.kernel.ledger.verify_chain()


def test_commercial_change_escalates_then_scoped_approval_is_consumed():
    session = OnlyAskProductSession()

    requested = session.request_price_change("39.00")

    assert requested.state.value == "escalated"
    assert requested.transition_id in session.pending
    assert session.workspace.checkout_price == "49.00"
    assert session.ask_count == 1

    approved = session.approve_once(requested.transition_id)

    assert approved.state.value == "verified"
    assert session.workspace.checkout_price == "39.00"
    assert session.envelope.grants[-1].remaining_uses == 0
    assert session.kernel.ledger.verify_chain()


def test_explicit_dns_prohibition_never_becomes_an_ask():
    session = OnlyAskProductSession()

    result = session.attempt_dns_change()

    assert result.state.value == "denied"
    assert result.decision.authority_basis == "deny:dns/*:*"
    assert session.ask_count == 0
    assert session.workspace.dns_target == "legacy.example.invalid"


def test_failed_mutation_is_recovered_to_predecessor_state():
    session = OnlyAskProductSession()
    before = session.workspace.homepage_html

    result = session.simulate_failed_repair()

    assert result.state.value == "recovered"
    assert result.verification_passed is False
    assert result.recovery_passed is True
    assert session.workspace.homepage_html == before
    assert session.recovered_count == 1


def test_external_directive_is_evidence_not_authority():
    session = OnlyAskProductSession()

    observed = session.observe_external_directive()

    assert observed["directive_like"] is True
    assert observed["disposition"] == "untrusted_evidence"
    assert session.kernel.ledger.verify_chain()


def test_showcase_leaves_exactly_one_genuine_human_decision_pending():
    session = OnlyAskProductSession()

    results = session.run_showcase()
    state = session.state()

    assert len(results) == 6
    assert state["metrics"]["asks"] == 1
    assert len(state["pending"]) == 1
    assert state["metrics"]["denied"] == 1
    assert state["metrics"]["recovered"] == 1
    assert state["ledger_valid"] is True


def test_console_approval_path_uses_pending_transition():
    console = OnlyAskConsole()

    requested = console.action("price", {"new_price": "39.00"})
    approved = console.approve(requested["transition_id"])

    assert requested["state"] == "escalated"
    assert approved["state"] == "verified"
    assert console.state()["workspace"]["checkout_price"] == "39.00"
