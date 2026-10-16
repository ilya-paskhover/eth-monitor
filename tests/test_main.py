from unittest.mock import MagicMock

import main


def test_test_flag_exit_code_reflects_send_result(mocker):
    monitor = MagicMock()
    mocker.patch("main.build_monitor", return_value=monitor)

    monitor.test.return_value = False
    assert main.main(["--test"]) == 1
    monitor.test.return_value = True
    assert main.main(["--test"]) == 0
