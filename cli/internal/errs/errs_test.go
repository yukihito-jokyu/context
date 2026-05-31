package errs

import (
	"errors"
	"os"
	"testing"
)

func TestWrap(t *testing.T) {
	err := Wrap("failed to stat", "/tmp/context", os.ErrPermission)
	if err == nil {
		t.Fatal("expected wrapped error")
	}
	if got, want := err.Error(), `failed to stat "/tmp/context": permission denied`; got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
	if !errors.Is(err, os.ErrPermission) {
		t.Fatalf("expected wrapped error to match os.ErrPermission, got %v", err)
	}
}

func TestWrapWithoutTarget(t *testing.T) {
	err := Wrap("failed to locate context repository root", "", os.ErrNotExist)
	if err == nil {
		t.Fatal("expected wrapped error")
	}
	if got, want := err.Error(), "failed to locate context repository root: file does not exist"; got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestWrapNil(t *testing.T) {
	if err := Wrap("failed", "/tmp/context", nil); err != nil {
		t.Fatalf("expected nil, got %v", err)
	}
}
