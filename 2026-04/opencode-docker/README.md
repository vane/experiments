build / run  

```bash
docker build -t opencode:1 -f Dockerfile .
```

```bash
docker run --rm -ti -v $(pwd):/project opencode:1 bash
```
