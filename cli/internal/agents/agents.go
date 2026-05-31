package agents

import (
	"io"
	"os"
	"path/filepath"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

func Exists(targetDir, name string) (bool, error) {
	path := filepath.Join(targetDir, name)
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, errs.Wrap("failed to stat "+name, path, err)
}

func Deploy(targetDir, sourceFile string) error {
	dstFile := filepath.Join(targetDir, "AGENTS.md")
	return copyFile(sourceFile, dstFile, "AGENTS.md")
}

func GenerateClaude(targetDir, sourceFile string) error {
	dstFile := filepath.Join(targetDir, "CLAUDE.md")
	return copyFile(sourceFile, dstFile, "CLAUDE.md")
}

func copyFile(sourceFile, dstFile, label string) error {
	in, err := os.Open(sourceFile)
	if err != nil {
		return errs.Wrap("failed to open "+label, sourceFile, err)
	}
	defer in.Close()

	out, err := os.Create(dstFile)
	if err != nil {
		return errs.Wrap("failed to create "+label, dstFile, err)
	}

	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return errs.Wrap("failed to copy "+label, dstFile, err)
	}
	if err := out.Close(); err != nil {
		return errs.Wrap("failed to close "+label, dstFile, err)
	}
	return nil
}
