import os
import chardet
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'rb') as f:
                raw = f.read()
                enc = chardet.detect(raw)['encoding']
                if enc and enc.lower() != 'utf-8':
                    print(path, enc)