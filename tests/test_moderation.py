import asyncio

from app.services.moderation import RuleBasedModerator


def check(text):
    return asyncio.run(RuleBasedModerator().check(text))


def test_allows_normal_tutoring():
    assert check("What is half of ten? Try counting it out.").allowed


def test_blocks_links_secrecy_and_contact_requests():
    assert not check("Visit www.example.com for the answer").allowed
    assert not check("Don't tell your parents about this").allowed
    assert not check("What's your home address?").allowed


def test_blocks_empty_output():
    assert not check("   ").allowed
