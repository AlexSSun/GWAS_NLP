# Automatic Table Information Extraction and Rule-Based Text Mining of GWAS publications

This repository provides the code for Automatic Table Information Extraction and Rule-Based Text Mining of GWAS publications.

## Abstract

Genome-wide association studies (GWAS) is the study of the association between genetic variants (single nucleotide polymorphisms, SNPs) and common disease traits, and GWAS Central is the world’s most comprehensive openly accessible repository of summary-level GWAS association information. However, the size of the repository and the speed of incorporating new studies are limited by the manual examination of publications. Automated text mining of scientific literature is a promising way to resolve this issue by processing publications automatically. This thesis describes three algorithms to improve the information recovery from GWAS publications. First, an algorithm outputs standardized JSON files for tables of various structures. Second, an ontology-based named entity recognition algorithm extracts disease traits from the main text. Third, a rule-based system using dependency parse tree extracts SNP and P-value associations from the main text. When compared with manually curated data from the GWAS Central database, 65% of disease traits are found across the articles in the corpus, and 38.4% of SNP and P-value associations reported in the database are recovered. However, the algorithm also recognizes many more potential traits, SNP and P-value candidates that are not found in the database. In conclusion, the application of these NLP algorithms for the first time on this type of dataset has shown that information that was previously manually extracted can also be recovered using faster, automated means.

# Getting Started

## 1. Main text extraction

Let `$FILEPATH` indicate the PubMed HTML file that will be processed, and let `$TARGET_DIR` indicate the target directory for output JSON file that contains the main text,

```bash
python maintext_clean.py -f $FILEPATH -t $TARGET_DIR
```

## 2. Standardized tables

Let `$FILEPATH` indicate the PubMed HTML file that will be processed, and let `$TARGET_DIR` indicate the target directory for output JSON file that contains the standardized tables,

```bash
python table_extracter.py -f $FILEPATH -t $TARGET_DIR
```

## 3. Named Entity Recognition of Disease Traits, SNP and P-value

Let `$FILEPATH` indicate the main text JSON file that will be processed, and let `$TARGET_DIR` indicate the target directory for output pkl file,

```bash
python maintext_keyword.py -f $FILEPATH -t $TARGET_DIR
```

## 4. SNP and P-value extraction

Let `$FILEPATH` indicate the main text JSON file that will be processed, and let `$TARGET_DIR` indicate the target directory for output pkl file,

```bash
python maintext_associations.py -f $FILEPATH -t $TARGET_DIR
```
