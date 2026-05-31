package main

import (
	"bytes"
	"errors"
	"io"
	"strings"
	"testing"
)

func TestRun(t *testing.T) {
	originalExecute := execute
	t.Cleanup(func() {
		execute = originalExecute
	})

	tests := []struct {
		name        string
		execErr     error
		wantCode    int
		wantErrText string
	}{
		{
			name:     "returns zero on success",
			wantCode: 0,
		},
		{
			name:        "prints error and returns one on failure",
			execErr:     errors.New("boom"),
			wantCode:    1,
			wantErrText: "boom\n",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			execute = func(args []string, in io.Reader, out, errOut io.Writer) error {
				return tt.execErr
			}

			var stdout bytes.Buffer
			var stderr bytes.Buffer

			got := run([]string{"deploy"}, strings.NewReader(""), &stdout, &stderr)
			if got != tt.wantCode {
				t.Fatalf("expected exit code %d, got %d", tt.wantCode, got)
			}
			if stderr.String() != tt.wantErrText {
				t.Fatalf("expected stderr %q, got %q", tt.wantErrText, stderr.String())
			}
		})
	}
}

func TestMain(t *testing.T) {
	originalExecute := execute
	originalExit := exit
	originalArgs := args
	originalStdin := stdin
	originalStdout := stdout
	originalStderr := stderr
	t.Cleanup(func() {
		execute = originalExecute
		exit = originalExit
		args = originalArgs
		stdin = originalStdin
		stdout = originalStdout
		stderr = originalStderr
	})

	execute = func(gotArgs []string, gotIn io.Reader, gotOut, gotErrOut io.Writer) error {
		if strings.Join(gotArgs, ",") != "deploy,alpha" {
			t.Fatalf("unexpected args: %v", gotArgs)
		}
		if gotIn != stdin || gotOut != stdout || gotErrOut != stderr {
			t.Fatal("main did not pass configured stdio")
		}
		return nil
	}

	args = func() []string { return []string{"deploy", "alpha"} }
	stdin = strings.NewReader("")
	stdout = &bytes.Buffer{}
	stderr = &bytes.Buffer{}

	exitCode := -1
	exit = func(code int) {
		exitCode = code
	}

	main()

	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d", exitCode)
	}
}
