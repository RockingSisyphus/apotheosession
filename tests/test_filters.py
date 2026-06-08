from apotheosession.filters import is_environment_context, is_user_message_text


def test_is_environment_context_detects_xml_block():
    text = "<environment_context>\n  <cwd>/tmp</cwd>\n</environment_context>"
    assert is_environment_context(text)


def test_is_environment_context_false_for_normal_text():
    assert not is_environment_context("hello world")


def test_is_user_message_text_skips_env_context():
    env = "<environment_context><cwd>/tmp</cwd></environment_context>"
    assert not is_user_message_text(env)


def test_is_user_message_text_skips_instructions():
    text = "<InstructionsForCodex>\nDo this\n</InstructionsForCodex>"
    assert not is_user_message_text(text)


def test_is_user_message_text_accepts_normal():
    assert is_user_message_text("What does this function do?")
