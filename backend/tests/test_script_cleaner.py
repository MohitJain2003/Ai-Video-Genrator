from app.pipeline.m06_voice import _clean_script_for_tts

def test_unicode_normalization():
    # Test emphasis cleaning
    assert _clean_script_for_tts("Hello *World*!") == "Hello World!"
    
    # Test Unicode spaces (narrow no-break space and non-breaking space)
    assert _clean_script_for_tts("Dec\u202f31\u00a02026") == "Dec 31 2026"
    
    # Test dashes (em-dash to comma-pause, non-breaking hyphen to normal hyphen)
    assert _clean_script_for_tts("salary $250k\u2014apply now") == "salary $250k, apply now"
    assert _clean_script_for_tts("self\u2011driving") == "self-driving"
    
    # Test quotes (curly quotes to straight quotes)
    assert _clean_script_for_tts("\u201cHello\u201d") == '"Hello"'
    assert _clean_script_for_tts("Don\u2019t") == "Don't"
    
    # Test pause markers
    assert _clean_script_for_tts("Stop.[PAUSE] Go.") == "Stop. Go."
    assert _clean_script_for_tts("Wait[PAUSE]here") == "Wait, here"
