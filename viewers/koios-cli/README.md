# Koios CLI (Zero-Dependency)

Zero‑dependency command‑line readers using Koios public REST.

## Constitution Reader

```bash
python3 read_constitution.py           # Epoch 608 (current), preview
python3 read_constitution.py 541       # Epoch 541 (historical)
python3 read_constitution.py 608 --save
python3 read_constitution.py 608 --verify
```

## Universal Scroll Reader

```bash
python3 read_scroll.py --list
python3 read_scroll.py constitution-e608 --save
python3 read_scroll.py hosky-png --save
python3 read_scroll.py architects-scroll --verify
```
