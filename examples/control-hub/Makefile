CC ?= cc
CFLAGS ?= -std=c99 -Wall -Wextra -Werror -O0 -g

.PHONY: all test
all: build/hub build/libhub.so

build:
	mkdir -p build

build/hub: hub.c hub.h main.c | build
	$(CC) $(CFLAGS) hub.c main.c -o $@

build/libhub.so: hub.c hub.h | build
	$(CC) $(CFLAGS) -shared -fPIC hub.c -o $@

test: all
	python3 -m unittest discover -s tests -v
