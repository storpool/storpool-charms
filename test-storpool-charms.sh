#!/bin/sh

set -e

spcharms='./storpool-charms.py'
testdir='../test'
common="${SP_CHARMS_REPO+-U $SP_CHARMS_REPO} -d $testdir"
space="${SP_SPACE:-storpool}"

do_test() {
	local python="$1"
	shift
	local args="$*"
	
	printf '\n\n======== Python "%s" args "%s"\n\n' "$python" "$args"

	if ! "$python" "$spcharms" $args; then
		printf '\n\n======== "%s %s %s" failed\n\n' "$python" "$spcharms" "$args" 1>&2
		exit 1
	fi

	printf '\n\n======== "%s %s %s" succeeded\n\n' "$python" "$spcharms" "$args"
}

for python in python2 python3; do
	rm -rf -- "$testdir"
	do_test "$python" "$common --help"
	if [ -e "$testdir" ]; then
		printf '"%s --help" created %s\n' "$python" "$testdir" 1>&2
		exit 1
	fi

	do_test "$python" "$common -N checkout"
	if [ -e "$testdir" ]; then
		printf '"%s -N" created %s\n' "$python" "$testdir" 1>&2
		exit 1
	fi
done

for python in python2 python3; do
	rm -rf -- "$testdir"
	mkdir -- "$testdir"
	do_test "$python" "$common checkout"
	if [ ! -d "$testdir/storpool-charms/charms/charm-storpool-block" ] || [ ! -d "$testdir/storpool-charms/interfaces/interface-storpool-service" ]; then
		printf '"%s checkout" did not create the expected directories\n' "$python" 1>&2
		exit 1
	fi

	do_test "$python" "$common -N pull"
	do_test "$python" "$common pull"

	do_test "$python" "$common -N build"
	do_test "$python" "$common build"

	do_test "$python" "$common -N deploy"

    do_test "$python" "$common -S $space generate-config"
done
