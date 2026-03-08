import logging

from eth_monitor.logger import setup_logger


def test_returns_logger():
    logger = setup_logger("test_returns_logger")
    assert isinstance(logger, logging.Logger)


def test_has_stderr_handler():
    logger = setup_logger("test_stderr_handler")
    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                       and not isinstance(h, logging.FileHandler)]
    assert stream_handlers


def test_file_handler_added(tmp_path):
    log_file = str(tmp_path / "test.log")
    logger = setup_logger("test_file_handler", log_file=log_file)
    file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers


def test_file_handler_skipped_on_invalid_path():
    """Should not raise even if the log file path is invalid."""
    logger = setup_logger("test_bad_path", log_file="/nonexistent_dir/sub/test.log")
    # At least the stderr handler must be present
    assert logger.handlers


def test_idempotent_second_call():
    """Calling setup_logger twice with the same name should not add duplicate handlers."""
    name = "test_idempotent"
    logger1 = setup_logger(name)
    handler_count = len(logger1.handlers)
    logger2 = setup_logger(name)
    assert len(logger2.handlers) == handler_count
