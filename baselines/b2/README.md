# B2 : Web-grounded single-call baseline

## Run

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python3 run.py         
```

Makes a single web-grounded call and writes the answer to `output.txt`.