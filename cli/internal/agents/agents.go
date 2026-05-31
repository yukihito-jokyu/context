package agents

import (
	"io"
	"os"
	"path/filepath"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

func Deploy(targetDir, sourceFile string) error {
	dstFile := filepath.Join(targetDir, "AGENTS.md")

	in, err := os.Open(sourceFile)
	if err != nil {
		return errs.Wrap("failed to open AGENTS.md", sourceFile, err)
	}
	defer in.Close()

	out, err := os.Create(dstFile)
	if err != nil {
		return errs.Wrap("failed to create AGENTS.md", dstFile, err)
	}

	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return errs.Wrap("failed to copy AGENTS.md", dstFile, err)
	}
	if err := out.Close(); err != nil {
		return errs.Wrap("failed to close AGENTS.md", dstFile, err)
	}
	return nil
}
