from unittest.mock import patch

from app.main import main


def test_main_starts_the_local_telephony_api() -> None:
    with patch("app.main.uvicorn.run") as run:
        main()

    run.assert_called_once_with(
        "app.telephony.server:app",
        host="127.0.0.1",
        port=8001,
    )
