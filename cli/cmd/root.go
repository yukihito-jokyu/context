package cmd

import (
	"fmt"
	"io"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

func Execute(args []string, in io.Reader, out, errOut io.Writer) error {
	if len(args) == 0 {
		return usageError("command is required")
	}

	switch args[0] {
	case "deploy":
		return newDeployCommand(in, out, errOut).run(args[1:])
	default:
		return usageError(fmt.Sprintf("unknown command: %s", args[0]))
	}
}

func usageError(message string) error {
	return fmt.Errorf("%w: %s\n\nUsage:\n  context deploy\n  context deploy <repo-name>", errs.ErrUsage, message)
}
