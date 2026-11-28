# Source books

Put public-domain plain-text books here, one file per book, and add a row
for each to `sources.csv`. The file name (without `.txt`) is the `book_id`.

## Where to get them

Project Gutenberg (https://www.gutenberg.org) works well. On a book's page,
download **"Plain Text UTF-8"**. The header and license footer are stripped
automatically by `collect_passages.py`.

## How many

The split needs whole books per set, at least 30 passages per length group
per set, and enough 100-199 word passages for watermarking. Aim for:

- **15 to 25 books**, by different authors and from different periods
- prose only: novels, essays, histories (skip poetry, plays, dictionaries)

More books = less correlation between passages = more honest error rates,
which the report has to discuss.

## sources.csv

```
book_id,title,author,url,license
austen_pride,Pride and Prejudice,Jane Austen,https://www.gutenberg.org/ebooks/1342,Public domain (Project Gutenberg)
```

Every book in this folder needs a row, otherwise it is skipped.
