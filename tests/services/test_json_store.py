import json
import threading

from app.infra.json_store import load_json, save_json, update_json


def test_save_is_atomic_and_leaves_no_temp_files(tmp_path):
    target = tmp_path / "data.json"
    save_json(target, {"a": 1})
    save_json(target, {"a": 2})
    assert json.loads(target.read_text()) == {"a": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]


def test_corrupt_file_is_quarantined_not_overwritten(tmp_path):
    target = tmp_path / "history.json"
    target.write_text('{"truncated": ', encoding="utf-8")
    assert load_json(target, default={}) == {}
    # Original evidence is preserved so a later save cannot destroy it.
    corrupt = [p for p in tmp_path.iterdir() if ".corrupt-" in p.name]
    assert len(corrupt) == 1
    assert corrupt[0].read_text() == '{"truncated": '


def test_update_json_loses_no_concurrent_updates(tmp_path):
    target = tmp_path / "counter.json"

    def bump(i: int) -> None:
        update_json(target, lambda d: d.__setitem__(f"k{i}", i), default={})

    threads = [threading.Thread(target=bump, args=(i,)) for i in range(25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(load_json(target)) == 25
