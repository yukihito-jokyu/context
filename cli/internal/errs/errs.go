package errs

import (
	"errors"
	"fmt"
)

var (
	ErrUsage                    = errors.New("usage error")
	ErrNoProjects               = errors.New("no projects found under projects/")
	ErrProjectSelectionMissing  = errors.New("project selection was not provided")
	ErrInvalidProjectSelection  = errors.New("invalid project selection")
	ErrRepoNameRequired         = errors.New("repo-name is required in non-interactive mode")
	ErrNoSkillsFound            = errors.New("no skills found to deploy")
	ErrSkillSelectionMissing    = errors.New("skill selection was not provided")
	ErrInvalidSkillSelection    = errors.New("invalid skill selection")
	ErrInvalidAgentsPath        = errors.New("invalid AGENTS.md path")
	ErrInvalidAgentsSelection   = errors.New("invalid AGENTS.md selection")
	ErrInvalidClaudeSelection   = errors.New("invalid CLAUDE.md selection")
	ErrInvalidContinueSelection = errors.New("invalid continue selection")
	ErrProjectNotFound          = errors.New("project not found")
	ErrInvalidProjectName       = errors.New("project name must be a single directory name under projects/")
	ErrContextRootNotFound      = errors.New("failed to locate context repository root")
	ErrNotDirectory             = errors.New("path is not a directory")
	ErrInvalidContextRepo       = errors.New("invalid CONTEXT_REPO")
)

type ProjectNotFoundError struct {
	Name string
}

func (e ProjectNotFoundError) Error() string {
	return fmt.Sprintf("project not found: %s", e.Name)
}

func (e ProjectNotFoundError) Unwrap() error {
	return ErrProjectNotFound
}

type InvalidProjectNameError struct {
	Name string
}

func (e InvalidProjectNameError) Error() string {
	return fmt.Sprintf("invalid project name: %s", e.Name)
}

func (e InvalidProjectNameError) Unwrap() error {
	return ErrInvalidProjectName
}

type Error struct {
	Op     string
	Target string
	Err    error
}

func (e Error) Error() string {
	if e.Target == "" {
		return fmt.Sprintf("%s: %v", e.Op, e.Err)
	}
	return fmt.Sprintf("%s %q: %v", e.Op, e.Target, e.Err)
}

func (e Error) Unwrap() error {
	return e.Err
}

func Wrap(op, target string, err error) error {
	if err == nil {
		return nil
	}
	return Error{
		Op:     op,
		Target: target,
		Err:    err,
	}
}
