# Copyright Axelera AI, 2025

from unittest.mock import Mock

from axelera.app import display, display_console


def test_count_as_bar():
    full = '\u2588'
    half = '\u258c'
    assert full * 8 == display_console._count_as_bar(0, 8, 0)
    assert full * 8 == display_console._count_as_bar(8, 8, 8)
    assert full * 4 + ' ' * 4 == display_console._count_as_bar(4, 8, 8)
    assert full * 3 + half + ' ' * 4 == display_console._count_as_bar(7, 8, 16)


def test_console_app_open_close_source():
    mock_frame = (Mock(), Mock(), False)
    new_frame = (Mock(), Mock(), False)
    with display_console.ConsoleApp() as app:
        app._current = {0: mock_frame, 1: mock_frame, 2: mock_frame}
        assert not app._closed_sources
        assert app.num_sources == 3
        app._handle_message(1, display._CloseSource(1, False))
        assert app._closed_sources == {1}
        assert app._current == {0: mock_frame, 2: mock_frame}
        assert app.num_sources == 2
        app._handle_message(1, display._Frame(1, *new_frame[:2]))
        # check new frames are ignored
        assert app._current == {0: mock_frame, 2: mock_frame}
        assert not app._pending_updates
        assert app.num_sources == 2
        app._handle_message(1, display._OpenSource(1))
        assert not app._closed_sources
        # After open message received - no restart until next frame received
        assert app._current == {0: mock_frame, 2: mock_frame}
        assert not app._pending_updates
        app._handle_message(1, display._Frame(1, *new_frame[:2]))
        assert app._current == {0: mock_frame, 1: new_frame, 2: mock_frame}
        assert app.num_sources == 3
        assert app._pending_updates == {1}


def test_console_app_close_source_reopen():
    mock_frame = (Mock(), Mock(), False)
    new_frame = (Mock(), Mock(), False)
    with display_console.ConsoleApp() as app:
        app._current = {0: mock_frame, 1: mock_frame, 2: mock_frame}
        assert not app._closed_sources
        assert app.num_sources == 3
        app._handle_message(1, display._CloseSource(1, True))
        assert not app._closed_sources
        assert app._current == {0: mock_frame, 2: mock_frame}
        assert app.num_sources == 2
        assert not app._pending_updates
        app._handle_message(1, display._Frame(1, *new_frame[:2]))
        assert app._current == {0: mock_frame, 1: new_frame, 2: mock_frame}
        assert app.num_sources == 3
        assert app._pending_updates == {1}
