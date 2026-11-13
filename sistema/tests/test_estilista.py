"""El estilista encuentra vidIQ en cualquier máquina: MCP local «viqiq» o el conector de la cuenta."""
import json

from estudio import estilista


def test_vidiq_local_si_existe(tmp_path):
    f = tmp_path / ".claude.json"
    f.write_text(json.dumps({"projects": {"/x": {"mcpServers": {"viqiq": {}}}}}))
    assert estilista.prefijo_vidiq(f) == "mcp__viqiq__vidiq_"


def test_vidiq_conector_de_la_cuenta_si_no_hay_local(tmp_path):
    f = tmp_path / ".claude.json"
    f.write_text(json.dumps({"mcpServers": {}}))
    assert estilista.prefijo_vidiq(f) == "mcp__claude_ai_vidiq__vidiq_"
    assert estilista.prefijo_vidiq(tmp_path / "no-existe.json") == "mcp__claude_ai_vidiq__vidiq_"
