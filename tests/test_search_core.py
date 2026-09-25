from westquant_core import Action, DeterministicBeamSearch, Evaluation, Objective, pareto_front


def test_deterministic_beam_search_keeps_best_actions():
    search = DeterministicBeamSearch(stages=("a", "b"), beam_width=1, objectives=(Objective("cost"),))

    def actions(stage, prefix):
        return [Action(stage, "x"), Action(stage, "y")]

    def evaluate(prefix):
        score = sum(0 if a.name == "y" else 10 for a in prefix)
        return Evaluation(success=True, metrics={"cost": score}, verification={"equivalence": "exact"})

    result = search.run(challenge_id="c", actions=actions, evaluate=evaluate)
    assert result.best is not None
    assert [a.name for a in result.best.prefix] == ["y", "y"]
    assert len(result.records(framework="fake")) == 4


def test_pareto_front():
    xs = [{"a": 1, "b": 5}, {"a": 2, "b": 2}, {"a": 3, "b": 6}]
    front = pareto_front(xs, lambda x: x, (Objective("a"), Objective("b")))
    assert xs[2] not in front
    assert xs[0] in front and xs[1] in front

def test_policy_record_validation():
    from westquant_core import validate_policy_record
    record={
        'schema_version':'wqt-policy-v0.1','framework':'x','challenge_id':'c','state_id':'s','next_state_id':'n',
        'step_index':0,'stage':'a','action':{'stage':'a','name':'x','parameters':{}},'success':True,'selectable':True,
        'verification':{},'metrics_before':{},'metrics_after':{},'kept_in_beam':True,'terminal':False,
    }
    assert validate_policy_record(record)==[]
