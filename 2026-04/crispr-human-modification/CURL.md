# Genomic Data Fetching Commands

This document contains the `curl` commands used to retrieve the 101bp genomic sequences flanking each target SNP from the UCSC Genome Browser API (hg38).

## Command List

### Brown/Blue (rs12913832)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28120421;end=28120522" > data/rs12913832.json
```

### Dark Brown (rs1800401)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28014856;end=28014957" > data/rs1800401.json
```

### Green (rs12203592)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=396271;end=396371" > data/rs12203592.json
```

### Hazel (rs1800407)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27985121;end=27985222" > data/rs1800407.json
```

### Amber (rs1540771)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr20;start=34138041;end=34138142" > data/rs1540771.json
```

### Grey (rs12896399)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92113228;end=92113329" > data/rs12896399.json
```

### Light Blue (rs16891982)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr5;start=33951505;end=33951606" > data/rs16891982.json
```

### Blue/Green (rs1393350)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89010926;end=89011027" > data/rs1393350.json
```

### Red (rs1042602)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89230507;end=89230607" > data/rs1042602.json
```
