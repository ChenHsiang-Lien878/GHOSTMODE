$python = "python"
if (Test-Path ".venv/Scripts/python.exe") {
	$python = ".venv/Scripts/python.exe"
}

& $python -m pip install -r requirements.txt
& $python app.py
