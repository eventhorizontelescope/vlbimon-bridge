#!/bin/bash

# usage: bash resolve-sqlite-wal.sh foo.db

sqlite3 $1 .schema > /dev/null

