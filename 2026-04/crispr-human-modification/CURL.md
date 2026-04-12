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

### Limbal/Pigmented Ring (rs4900109)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92296996;end=92297097" > data/rs4900109.json
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

## Teeth Morphology

### Tooth Agenesis (rs4904210)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=36666497;end=36666598" > data/rs4904210.json
```

### Tooth Agenesis (rs8670)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr4;start=4863098;end=4863199" > data/rs8670.json
```

### Tooth Shape/Size (rs10168648)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr2;start=35201976;end=35202077" > data/rs10168648.json
```

### Tooth Size (rs3866831)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr4;start=110810907;end=110811008" > data/rs3866831.json
```

### Incisor Shoveling (rs3827760)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr2;start=108897094;end=108897195" > data/rs3827760.json
```

## Eyebrow Traits

### Eyebrow Thickness (rs1345417)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr3;start=181794112;end=181794213" > data/rs1345417.json
```

### Eyebrow Thickness (rs12651896)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr5;start=73206151;end=73206252" > data/rs12651896.json
```

### Eyebrow Thickness (rs112458845)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr3;start=138956848;end=138956949" > data/rs112458845.json
```

### Synophrys (rs4849721)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr2;start=118786395;end=118786496" > data/rs4849721.json
```

### Eyebrow Thickness (rs16833231)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr1;start=151430604;end=151430705" > data/rs16833231.json
```

## Martin-Schultz Scale (1a-16)

### 1a: Pale Blue Iris (rs4778219)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28126491;end=28126592" > data/rs4778219.json
```

### 1b: Light Blue Iris (rs8024968)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28132515;end=28132616" > data/rs8024968.json
```

### 1c: Sky Blue Iris (rs7183877)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28138182;end=28138183" > data/rs7183877.json
```

### 2a: Blue Iris (rs11638447)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28144839;end=28144840" > data/rs11638447.json
```

### 2b: Dark Blue Iris (rs3935591)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28151404;end=28151405" > data/rs3935591.json
```

### 3: Blue-Gray Iris (rs238538)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92045234;end=92045335" > data/rs238538.json
```

### 4a: Light Gray Iris (rs12896399)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92113228;end=92113329" > data/rs12896399.json
```

### 4b: Dark Gray Iris (rs12976356)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92156789;end=92156890" > data/rs12976356.json
```

### 5: Blue-Gray with Yellow/Brown Spots (rs4778138)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28090623;end=28090724" > data/rs4778138.json
```

### 6: Gray-Green with Yellow/Brown Spots (rs1126809)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89284742;end=89284843" > data/rs1126809.json
```

### 7: Green Iris (rs12203592)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=396271;end=396372" > data/rs12203592.json
```

### 8: Green with Yellow/Brown Spots (rs1393350)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89010926;end=89011027" > data/rs1393350.json
```

### 9: Amber Iris (rs1540771)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr20;start=34138041;end=34138142" > data/rs1540771.json
```

### 10: Hazel Iris (rs1800407)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27985121;end=27985222" > data/rs1800407.json
```

### 11: Light Brown Iris (rs1667394)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28284985;end=28285086" > data/rs1667394.json
```

### 12: Medium Brown Iris (rs12194118)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27890123;end=27890224" > data/rs12194118.json
```

### 13: Dark Brown/Mahogany Iris (rs1800401)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28014856;end=28014957" > data/rs1800401.json
```

### 14: Brown-Black (Deep Brown) Iris (rs2238288)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=401182;end=401283" > data/rs2238288.json
```

### 15: Black-Brown Iris (rs1695778)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr5;start=33968515;end=33968616" > data/rs1695778.json
```

### 16: Black Iris (rs12194118-AA)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27890123;end=27890224" > data/rs12194118_aa.json
```

### 4a: Light Gray Iris (rs12896399)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92113228;end=92113329" > data/rs12896399.json
```

### 4b: Dark Gray Iris (rs12976356)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr14;start=92156789;end=92156890" > data/rs12976356.json
```

### 5: Blue-Gray with Yellow/Brown Spots (rs4778138)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28090622;end=28090623" > data/rs4778138.json
```

### 6: Gray-Green with Yellow/Brown Spots (rs1126809)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89284741;end=89284742" > data/rs1126809.json
```

### 7: Green Iris (rs12203592)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=396271;end=396372" > data/rs12203592.json
```

### 8: Green with Yellow/Brown Spots (rs1393350)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=89010926;end=89011027" > data/rs1393350.json
```

### 9: Amber Iris (rs1540771)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr20;start=34138041;end=34138142" > data/rs1540771.json
```

### 10: Hazel Iris (rs1800407)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27985121;end=27985222" > data/rs1800407.json
```

### 11: Light Brown Iris (rs1667394)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28284984;end=28284985" > data/rs1667394.json
```

### 12: Medium Brown Iris (rs12194118)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27920567;end=27920568" > data/rs12194118.json
```

### 13: Dark Brown/Mahogany Iris (rs1800401)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=28014856;end=28014957" > data/rs1800401.json
```

### 14: Brown-Black (Deep Brown) Iris (rs2238288)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr6;start=401182;end=401183" > data/rs2238288.json
```

### 15: Black-Brown Iris (rs1695778)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr5;start=33968515;end=33968516" > data/rs1695778.json
```

### 16: Black Iris (rs12194118-AA)
```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr15;start=27890123;end=27890124" > data/rs12194118_aa.json
```
