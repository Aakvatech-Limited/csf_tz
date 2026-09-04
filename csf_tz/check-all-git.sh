#!/bin/bash

for dir in apps/* ; do
	if [ -d "$dir" ]; then
		echo "$dir"
		cd $dir
		git status
		cd ../..
	fi
done
