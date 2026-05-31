package cmd

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

func TestExecuteUsageErrors(t *testing.T) {
	tests := []struct {
		name        string
		args        []string
		wantMessage string
	}{
		{
			name:        "requires command",
			args:        nil,
			wantMessage: "command is required",
		},
		{
			name:        "rejects unknown command",
			args:        []string{"unknown"},
			wantMessage: "unknown command: unknown",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := Execute(tt.args, strings.NewReader(""), &strings.Builder{}, &strings.Builder{})
			if !errors.Is(err, errs.ErrUsage) {
				t.Fatalf("expected usage error, got %v", err)
			}
			if !strings.Contains(err.Error(), tt.wantMessage) {
				t.Fatalf("expected message %q in %q", tt.wantMessage, err.Error())
			}
		})
	}
}

func TestUsageError(t *testing.T) {
	err := usageError("bad input")
	if !errors.Is(err, errs.ErrUsage) {
		t.Fatalf("expected usage error, got %v", err)
	}
	if !strings.Contains(err.Error(), "context deploy <repo-name>") {
		t.Fatalf("expected usage text, got %q", err.Error())
	}
}

func TestExecuteDeploy(t *testing.T) {
	repoRoot := makeContextRepo(t, []string{"alpha"})
	originalStdinStat := stdinStat
	originalWD, err := os.Getwd()
	if err != nil {
		t.Fatalf("failed to get working directory: %v", err)
	}
	t.Cleanup(func() {
		stdinStat = originalStdinStat
		if chdirErr := os.Chdir(originalWD); chdirErr != nil {
			t.Fatalf("failed to restore working directory: %v", chdirErr)
		}
	})
	if err := os.Chdir(filepath.Join(repoRoot, "cli")); err != nil {
		t.Fatalf("failed to chdir: %v", err)
	}
	t.Setenv("CONTEXT_REPO", repoRoot)
	stdinStat = func() (os.FileInfo, error) {
		return fileInfoStub{mode: 0}, nil
	}

	var stdout bytes.Buffer
	var stderr bytes.Buffer

	err = Execute([]string{"deploy", "alpha"}, strings.NewReader(""), &stdout, &stderr)
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}
	if !strings.Contains(stdout.String(), "project: alpha") {
		t.Fatalf("expected selected project in stdout, got %q", stdout.String())
	}
	if !strings.Contains(stderr.String(), "warning: current directory is not a git repository") {
		t.Fatalf("expected git warning, got %q", stderr.String())
	}
}
