#!/usr/bin/env python
import sys
import bots.botslib as botslib
import bots.botsglobal as botsglobal
import bots.botsinit as botsinit

"""
No plugin needed.
Run in command line.
Should give no errors.
Tests various encodings in error messages.
"""

def testraise(expect, msg2, *args, **kwargs):
    """
    Raises a BotsError and checks whether the caught exception's string
    matches the expected text.
    """
    try:
        raise botslib.BotsError(msg2, *args, **kwargs)
    except Exception as msg:
        # Ensure we have a standard string representation.
        if not isinstance(msg, str):
            msg = str(msg)

        if expect:
            if str(expect) != msg.strip():
                print(f"Expected: {expect}")
                print(f"Received: {msg.strip()}")

        # Display any traceback text if needed.
        txt = botslib.txtexc()
        if not isinstance(txt, str):
            print("Error in botslib.txtexc():")
            print(txt)


def testrun():
    """
    Tests multiple ways of raising and catching errors with string/bytes/encodings.
    """
    print("\n--- Starting test run ---")

    # Normal usage: placeholders with dict or kw-arguments
    testraise("", "", {"test1": "test1", "test2": "test2", "test3": "test3"})
    testraise("0test", "0test", {"test1": "test1", "test2": "test2", "test3": "test3"})
    testraise("0test test1 test2",
              "0test %(test1)s %(test2)s %(test4)s",
              {"test1": "test1", "test2": "test2", "test3": "test3"})
    testraise("1test test1 test2 test3",
              "1test %(test1)s %(test2)s %(test3)s",
              {"test1": "test1", "test2": "test2", "test3": "test3"})
    testraise("2test test1 test2 test3",
              "2test %(test1)s %(test2)s %(test3)s",
              {"test1": "test1", "test2": "test2", "test3": "test3"})

    # Different inputs to BotsError
    testraise("3test", "3test")
    testraise("4test test1 test2",
              "4test %(test1)s %(test2)s %(test3)s",
              {"test1": "test1", "test2": "test2"})
    testraise("5test test1 test2",
              "5test %(test1)s %(test2)s %(test3)s",
              test1="test1", test2="test2")
    testraise("6test", "6test %(test1)s %(test2)s %(test3)s", "test1")
    testraise("7test ['test1', 'test2']",
              "7test %(test1)s %(test2)s %(test3)s",
              test1=["test1", "test2"])
    testraise("8test {'test1': 'test1', 'test2': 'test2'}",
              "8test %(test1)s %(test2)s %(test3)s",
              test1={"test1": "test1", "test2": "test2"})
    testraise("9test [<module ...> , <module ...>]",
              "9test %(test1)s %(test2)s %(test3)s",
              test1=[botslib, botslib])

    # Unicode chars in messages and placeholders
    testraise("12test test1 test2 test3",
              "12test %(test1)s %(test2)s %(test3)s",
              {"test1": "test1", "test2": "test2", "test3": "test3"})
    testraise("13testéëúûüăŸơȂ test1éëúûüăŸơȂ test2éëúûüăŸơȂ test3éëúûüăŸơȂ",
              "13testéëúûüăŸơȂ %(test1)s %(test2)s %(test3)s",
              {"test1": "test1éëúûüăŸơȂ",
               "test2": "test2éëúûüăŸơȂ",
               "test3": "test3éëúûüăŸơȂ"})
    testraise("14testéëúûüăŸơȂ test1éëúûüăŸơȂ",
              # Here we encode the message in UTF-8 to mimic old Python2 approach
              "14testéëúûüăŸơȂ %(test1)s".encode("utf_8"),
              {"test1": "test1éëúûüăŸơȂ".encode("utf_8")})
    testraise("15test test1",
              "15test %(test1)s",
              {"test1": "test1".encode("utf_16")})
    testraise("16testéëúûüăŸơȂ test1éëúûüăŸơȂ",
              "16testéëúûüăŸơȂ %(test1)s",
              {"test1": "test1éëúûüăŸơȂ".encode("utf_16")})
    testraise("17testéëúûüăŸơȂ test1éëúûüăŸơȂ",
              "17testéëúûüăŸơȂ %(test1)s",
              {"test1": "test1éëúûüăŸơȂ".encode("utf_32")})
    testraise("18testéëúûü test1éëúûü",
              "18testéëúûü %(test1)s",
              {"test1": "test1éëúûü".encode("latin_1")})
    testraise("19test test1",
              "19test %(test1)s",
              {"test1": "test1".encode("cp500")})
    testraise("20test test1",
              "20test %(test1)s",
              {"test1": "test1".encode("euc_jp")})

    # Large-range test in codepoints up to 65535
    l = []
    for i in range(256**2):  # 65536
        l.append(chr(i))
    s = "".join(l)
    print(type(s))
    testraise("", s)  # Raise with a giant unicode string

    s2 = s.encode("utf-8")  # Convert to bytes in UTF-8
    print(type(s2))
    testraise("", s2)

    # ISO-8859-1 bytes test
    l = list(range(256))  # 0..255
    s_bytes = bytes(l)
    print(type(s_bytes))
    testraise("", s_bytes)

    # Decode from latin_1 -> str
    s2 = s_bytes.decode("latin_1")
    print(type(s2))
    testraise("", s2)


if __name__ == "__main__":
    botsinit.generalinit("config")
    botsinit.initbotscharsets()
    botsglobal.logger = botsinit.initenginelogging("engine")
    botsglobal.ini.set("settings", "debug", "False")
    testrun()
    botsglobal.ini.set("settings", "debug", "True")
    testrun()
