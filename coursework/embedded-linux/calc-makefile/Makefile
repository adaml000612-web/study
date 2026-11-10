CC = gcc
CFLAGS = -Wall -g -fno-builtin-div
TARGET = calc
SRCS = main.c add.c dec.c mil.c div.c
OBJS = $(SRCS:.c=.o)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) $^ -o $@

%.o: %.c main.h
	$(CC) $(CFLAGS) -c $< -o $@

.PHONY: clean
clean:
	rm -f $(OBJS) $(TARGET)
