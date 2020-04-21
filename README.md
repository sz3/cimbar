The grader:

```
python -m cimbar.cimbar --dark --deskew=0 --ecc=0 4.png /tmp/clean.py
python -m cimbar.cimbar --dark --ecc=0 samples/4color1.jpg /tmp/unclean.py
python -m cimbar.grader --dark /tmp/clean.py /tmp/unclean.py
```

Fitness:

```
python -m cimbar.cimbar --dark --deskew=0 --ecc=0 4.png /tmp/clean.py
python -m cimbar.fitness --dark /tmp/clean.py samples/4color1.jpg

```
