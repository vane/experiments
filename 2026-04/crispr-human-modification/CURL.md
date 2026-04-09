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

### Sectoral Heterochromia (rs121434257)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr2;start=222216584;end=222216685" > data/rs121434257.json
```

## Nose Morphology

### Nose Wing Breadth (rs927833)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr20;start=22060888;end=22060989" > data/rs927833.json
```

### Nose Protrusion (rs2045323)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr4;start=153910696;end=153910797" > data/rs2045323.json
```

### Columella Inclination (rs12644248)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr4;start=154314189;end=154314290" > data/rs12644248.json
```

### Nose Width (rs2206437)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr20;start=4863897;end=4863998" > data/rs2206437.json
```

### Nose Length (rs647711)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr1;start=116167613;end=116167714" > data/rs647711.json
```

## Ear Morphology

### Ear Shape/Protrusion (rs3827760)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr2;start=108897094;end=108897195" > data/rs3827760.json
```

### Lobe Attachment (rs6802174)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr3;start=139287771;end=139287872" > data/rs6802174.json
```

### Vertical Ear Length (rs7812632)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr8;start=121878604;end=121878705" > data/rs7812632.json
```

### Darwin's Tubercle (rs1948400)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr3;start=139265353;end=139265454" > data/rs1948400.json
```

### Lobe Size (rs263156)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=142586327;end=142586428" > data/rs263156.json
```
