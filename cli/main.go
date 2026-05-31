package main

import (
	"fmt"
	"io"
	"os"

	"github.com/yukihito-jokyu/context/cli/cmd"
)

var (
	execute           = cmd.Execute
	exit              = os.Exit
	args              = func() []string { return os.Args[1:] }
	stdin   io.Reader = os.Stdin
	stdout  io.Writer = os.Stdout
	stderr  io.Writer = os.Stderr
)

func run(args []string, in io.Reader, out, errOut io.Writer) int {
	if err := execute(args, in, out, errOut); err != nil {
		fmt.Fprintln(errOut, err)
		return 1
	}
	return 0
}

func main() {
	exit(run(args(), stdin, stdout, stderr))
}
