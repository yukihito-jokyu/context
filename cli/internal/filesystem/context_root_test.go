package filesystem

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResolve(t *testing.T) {
	tests := []struct {
		name            string
		setup           func(*testing.T) (ContextLocator, ResolveParams, string)
		wantResolvedBy  string
		wantErrContains []string
	}{
		{
			name: "uses explicit root",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				root := makeContextRoot(t)
				return ContextLocator{
					executablePath: func() (string, error) {
						return filepath.Join(t.TempDir(), "bin", "context"), nil
					},
				}, ResolveParams{ExplicitRoot: root, StartDir: t.TempDir()}, root
			},
			wantResolvedBy: "CONTEXT_REPO",
		},
		{
			name: "rejects invalid explicit root",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				dir := t.TempDir()
				if err := os.Mkdir(filepath.Join(dir, "utils"), 0o755); err != nil {
					t.Fatalf("failed to create utils dir: %v", err)
				}
				return NewContextLocator(), ResolveParams{ExplicitRoot: dir, StartDir: dir}, ""
			},
			wantErrContains: []string{"invalid CONTEXT_REPO", "projects/", "cli/"},
		},
		{
			name: "falls back to parent search",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				root := makeContextRoot(t)
				startDir := filepath.Join(root, "projects", "context")
				if err := os.MkdirAll(startDir, 0o755); err != nil {
					t.Fatalf("failed to create start dir: %v", err)
				}
				return ContextLocator{
					executablePath: func() (string, error) {
						return filepath.Join(t.TempDir(), "bin", "context"), nil
					},
				}, ResolveParams{StartDir: startDir}, root
			},
			wantResolvedBy: "cwd-parent-search",
		},
		{
			name: "uses executable relative search",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				root := makeContextRoot(t)
				executableDir := filepath.Join(root, "cli", "bin")
				if err := os.MkdirAll(executableDir, 0o755); err != nil {
					t.Fatalf("failed to create executable dir: %v", err)
				}
				return ContextLocator{
					executablePath: func() (string, error) {
						return filepath.Join(executableDir, "context"), nil
					},
				}, ResolveParams{StartDir: t.TempDir()}, root
			},
			wantResolvedBy: "executable-relative",
		},
		{
			name: "ignores executable lookup error and falls back to parent search",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				root := makeContextRoot(t)
				startDir := filepath.Join(root, "cli")
				return ContextLocator{
					executablePath: func() (string, error) {
						return "", os.ErrPermission
					},
				}, ResolveParams{StartDir: startDir}, root
			},
			wantResolvedBy: "cwd-parent-search",
		},
		{
			name: "returns explicit root inspection error",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				originalResolveAbsPath := resolveAbsPath
				resolveAbsPath = func(string) (string, error) { return "", os.ErrInvalid }
				t.Cleanup(func() {
					resolveAbsPath = originalResolveAbsPath
				})
				return NewContextLocator(), ResolveParams{ExplicitRoot: "/tmp/context", StartDir: t.TempDir()}, ""
			},
			wantErrContains: []string{"failed to resolve path"},
		},
		{
			name: "returns not found guidance",
			setup: func(t *testing.T) (ContextLocator, ResolveParams, string) {
				startDir := t.TempDir()
				return ContextLocator{
					executablePath: func() (string, error) {
						return filepath.Join(t.TempDir(), "bin", "context"), nil
					},
				}, ResolveParams{StartDir: startDir}, ""
			},
			wantErrContains: []string{"failed to locate context repository root", "Set CONTEXT_REPO"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			locator, params, wantPath := tt.setup(t)
			resolved, err := locator.Resolve(params)
			if len(tt.wantErrContains) == 0 && err != nil {
				t.Fatalf("Resolve returned error: %v", err)
			}
			if len(tt.wantErrContains) > 0 {
				if err == nil {
					t.Fatal("expected error")
				}
				for _, part := range tt.wantErrContains {
					if !strings.Contains(err.Error(), part) {
						t.Fatalf("expected %q in error %q", part, err.Error())
					}
				}
				return
			}
			if resolved.Path != wantPath {
				t.Fatalf("expected root %q, got %q", wantPath, resolved.Path)
			}
			if resolved.ResolvedBy != tt.wantResolvedBy {
				t.Fatalf("expected resolution %q, got %q", tt.wantResolvedBy, resolved.ResolvedBy)
			}
		})
	}
}

func TestSearchParents(t *testing.T) {
	root := makeContextRoot(t)
	startDir := filepath.Join(root, "cli", "nested", "dir")
	if err := os.MkdirAll(startDir, 0o755); err != nil {
		t.Fatalf("failed to create nested dir: %v", err)
	}

	resolved, ok, err := searchParents(startDir)
	if err != nil {
		t.Fatalf("searchParents returned error: %v", err)
	}
	if !ok {
		t.Fatal("expected root to be found")
	}
	if resolved.Path != root {
		t.Fatalf("expected %q, got %q", root, resolved.Path)
	}
}

func TestSearchParentsReturnsInspectError(t *testing.T) {
	originalResolveAbsPath := resolveAbsPath
	resolveAbsPath = func(string) (string, error) { return "", os.ErrInvalid }
	t.Cleanup(func() {
		resolveAbsPath = originalResolveAbsPath
	})

	_, ok, err := searchParents(t.TempDir())
	if err == nil {
		t.Fatal("expected error")
	}
	if ok {
		t.Fatal("did not expect root to be found")
	}
}

func TestContextRootHelpers(t *testing.T) {
	root := ContextRoot{Path: "/tmp/context"}
	tests := []struct {
		name string
		got  string
		want string
	}{
		{name: "projects dir", got: root.ProjectsDir(), want: "/tmp/context/projects"},
		{name: "shared skills dir", got: root.UtilsSkillsDir(), want: "/tmp/context/utils/skills"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.got != tt.want {
				t.Fatalf("expected %q, got %q", tt.want, tt.got)
			}
		})
	}
}

func TestInspectRoot(t *testing.T) {
	tests := []struct {
		name            string
		setup           func(*testing.T) string
		wantMissing     []string
		wantComplete    bool
		wantSharedSkill bool
		wantErrText     string
	}{
		{
			name: "marks complete root with shared skills",
			setup: func(t *testing.T) string {
				return makeContextRoot(t)
			},
			wantComplete:    true,
			wantSharedSkill: true,
		},
		{
			name: "reports missing directories",
			setup: func(t *testing.T) string {
				return t.TempDir()
			},
			wantMissing: []string{"projects/", "utils/", "cli/"},
		},
		{
			name: "reports missing directories for nonexistent path",
			setup: func(t *testing.T) string {
				return filepath.Join(t.TempDir(), "missing")
			},
			wantMissing: []string{"projects/", "utils/", "cli/"},
		},
		{
			name: "rejects file path",
			setup: func(t *testing.T) string {
				path := filepath.Join(t.TempDir(), "context.txt")
				if err := os.WriteFile(path, []byte("file"), 0o644); err != nil {
					t.Fatalf("failed to create file: %v", err)
				}
				return path
			},
			wantErrText: "path is not a directory",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			root, missing, err := inspectRoot(tt.setup(t))
			if tt.wantErrText == "" && err != nil {
				t.Fatalf("inspectRoot returned error: %v", err)
			}
			if tt.wantErrText != "" {
				if err == nil || !strings.Contains(err.Error(), tt.wantErrText) {
					t.Fatalf("expected error containing %q, got %v", tt.wantErrText, err)
				}
				return
			}
			if strings.Join(missing, ",") != strings.Join(tt.wantMissing, ",") {
				t.Fatalf("expected missing %v, got %v", tt.wantMissing, missing)
			}
			if root.Complete != tt.wantComplete {
				t.Fatalf("expected complete=%t, got %t", tt.wantComplete, root.Complete)
			}
			if root.SharedSkillsExists != tt.wantSharedSkill {
				t.Fatalf("expected shared skills=%t, got %t", tt.wantSharedSkill, root.SharedSkillsExists)
			}
		})
	}
}

func TestHasDirectory(t *testing.T) {
	dir := t.TempDir()
	file := filepath.Join(dir, "file.txt")
	if err := os.WriteFile(file, []byte("file"), 0o644); err != nil {
		t.Fatalf("failed to create file: %v", err)
	}

	tests := []struct {
		name string
		path string
		want bool
	}{
		{name: "returns true for directory", path: dir, want: true},
		{name: "returns false for missing path", path: filepath.Join(dir, "missing"), want: false},
		{name: "returns false for file", path: file, want: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := hasDirectory(tt.path)
			if err != nil {
				t.Fatalf("hasDirectory returned error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("expected %t, got %t", tt.want, got)
			}
		})
	}
}

func TestHasDirectoryReturnsStatError(t *testing.T) {
	originalStatPath := statPath
	statPath = func(string) (os.FileInfo, error) { return nil, os.ErrPermission }
	t.Cleanup(func() {
		statPath = originalStatPath
	})

	_, err := hasDirectory("/tmp/context")
	if err == nil || !strings.Contains(err.Error(), "failed to stat") {
		t.Fatalf("expected stat error, got %v", err)
	}
}

func TestInspectRootReturnsStatError(t *testing.T) {
	originalStatPath := statPath
	statPath = func(string) (os.FileInfo, error) { return nil, os.ErrPermission }
	t.Cleanup(func() {
		statPath = originalStatPath
	})

	_, _, err := inspectRoot(t.TempDir())
	if err == nil || !strings.Contains(err.Error(), "failed to stat") {
		t.Fatalf("expected stat error, got %v", err)
	}
}

func TestInspectRootReturnsChildStatError(t *testing.T) {
	root := makeContextRoot(t)
	originalStatPath := statPath
	statPath = func(path string) (os.FileInfo, error) {
		if path == filepath.Join(root, "projects") {
			return nil, os.ErrPermission
		}
		return originalStatPath(path)
	}
	t.Cleanup(func() {
		statPath = originalStatPath
	})

	_, _, err := inspectRoot(root)
	if err == nil || !strings.Contains(err.Error(), "failed to stat") {
		t.Fatalf("expected child stat error, got %v", err)
	}
}

func TestInspectRootReturnsSharedSkillsError(t *testing.T) {
	root := makeContextRoot(t)
	originalStatPath := statPath
	statPath = func(path string) (os.FileInfo, error) {
		if path == filepath.Join(root, "utils", "skills") {
			return nil, os.ErrPermission
		}
		return originalStatPath(path)
	}
	t.Cleanup(func() {
		statPath = originalStatPath
	})

	_, _, err := inspectRoot(root)
	if err == nil || !strings.Contains(err.Error(), "failed to stat") {
		t.Fatalf("expected shared skills stat error, got %v", err)
	}
}

func TestResolveReturnsExecutableSearchError(t *testing.T) {
	originalResolveAbsPath := resolveAbsPath
	resolveAbsPath = func(string) (string, error) { return "", os.ErrInvalid }
	t.Cleanup(func() {
		resolveAbsPath = originalResolveAbsPath
	})

	locator := ContextLocator{
		executablePath: func() (string, error) {
			return filepath.Join(t.TempDir(), "bin", "context"), nil
		},
	}

	_, err := locator.Resolve(ResolveParams{StartDir: t.TempDir()})
	if err == nil || !strings.Contains(err.Error(), "failed to resolve path") {
		t.Fatalf("expected executable search error, got %v", err)
	}
}

func TestResolveReturnsStartDirSearchError(t *testing.T) {
	originalResolveAbsPath := resolveAbsPath
	resolveAbsPath = func(string) (string, error) { return "", os.ErrInvalid }
	t.Cleanup(func() {
		resolveAbsPath = originalResolveAbsPath
	})

	locator := ContextLocator{
		executablePath: func() (string, error) {
			return "", os.ErrPermission
		},
	}

	_, err := locator.Resolve(ResolveParams{StartDir: t.TempDir()})
	if err == nil || !strings.Contains(err.Error(), "failed to resolve path") {
		t.Fatalf("expected start dir search error, got %v", err)
	}
}

func TestExplicitRootError(t *testing.T) {
	err := explicitRootError("/tmp/context", []string{"projects/", "cli/"})
	text := err.Error()
	for _, part := range []string{"invalid CONTEXT_REPO", "/tmp/context", "projects/, cli/"} {
		if !strings.Contains(text, part) {
			t.Fatalf("expected %q in error %q", part, text)
		}
	}
}

func makeContextRoot(t *testing.T) string {
	t.Helper()

	root := t.TempDir()
	for _, dir := range []string{"projects", "utils/skills", "cli"} {
		if err := os.MkdirAll(filepath.Join(root, dir), 0o755); err != nil {
			t.Fatalf("failed to create %s: %v", dir, err)
		}
	}
	return root
}
