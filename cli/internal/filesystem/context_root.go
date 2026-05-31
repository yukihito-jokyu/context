package filesystem

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/yukihito-jokyu/context/cli/internal/errs"
)

type ResolveParams struct {
	ExplicitRoot string
	StartDir     string
}

type ContextRoot struct {
	Path               string
	ResolvedBy         string
	Complete           bool
	SharedSkillsExists bool
}

func (r ContextRoot) ProjectsDir() string {
	return filepath.Join(r.Path, "projects")
}

func (r ContextRoot) UtilsSkillsDir() string {
	return filepath.Join(r.Path, "utils", "skills")
}

type ContextLocator struct {
	executablePath func() (string, error)
}

var (
	resolveAbsPath = filepath.Abs
	statPath       = os.Stat
)

func NewContextLocator() ContextLocator {
	return ContextLocator{executablePath: os.Executable}
}

func (l ContextLocator) Resolve(params ResolveParams) (ContextRoot, error) {
	if strings.TrimSpace(params.ExplicitRoot) != "" {
		root, missing, err := inspectRoot(params.ExplicitRoot)
		if err != nil {
			return ContextRoot{}, err
		}
		if len(missing) > 0 {
			return ContextRoot{}, explicitRootError(root.Path, missing)
		}
		root.ResolvedBy = "CONTEXT_REPO"
		return root, nil
	}

	if executable, err := l.executablePath(); err == nil {
		if root, ok, err := searchParents(filepath.Dir(executable)); err != nil {
			return ContextRoot{}, err
		} else if ok {
			root.ResolvedBy = "executable-relative"
			return root, nil
		}
	}

	if root, ok, err := searchParents(params.StartDir); err != nil {
		return ContextRoot{}, err
	} else if ok {
		root.ResolvedBy = "cwd-parent-search"
		return root, nil
	}

	return ContextRoot{}, fmt.Errorf(
		"%w. Set CONTEXT_REPO or run the command inside a context repository tree with projects/, utils/, and cli/",
		errs.ErrContextRootNotFound,
	)
}

func searchParents(start string) (ContextRoot, bool, error) {
	current := filepath.Clean(start)
	for {
		root, missing, err := inspectRoot(current)
		if err != nil {
			return ContextRoot{}, false, err
		}
		if len(missing) == 0 {
			return root, true, nil
		}

		parent := filepath.Dir(current)
		if parent == current {
			return ContextRoot{}, false, nil
		}
		current = parent
	}
}

func inspectRoot(path string) (ContextRoot, []string, error) {
	absPath, err := resolveAbsPath(path)
	if err != nil {
		return ContextRoot{}, nil, errs.Wrap("failed to resolve path", path, err)
	}

	info, err := statPath(absPath)
	if err != nil {
		if os.IsNotExist(err) {
			return ContextRoot{Path: absPath}, []string{"projects/", "utils/", "cli/"}, nil
		}
		return ContextRoot{}, nil, errs.Wrap("failed to stat", absPath, err)
	}
	if !info.IsDir() {
		return ContextRoot{}, nil, fmt.Errorf("%w: %s", errs.ErrNotDirectory, absPath)
	}

	required := []string{"projects", "utils", "cli"}
	missing := make([]string, 0, len(required))
	for _, name := range required {
		if ok, err := hasDirectory(filepath.Join(absPath, name)); err != nil {
			return ContextRoot{}, nil, err
		} else if !ok {
			missing = append(missing, name+"/")
		}
	}

	sharedSkills, err := hasDirectory(filepath.Join(absPath, "utils", "skills"))
	if err != nil {
		return ContextRoot{}, nil, err
	}

	return ContextRoot{
		Path:               absPath,
		Complete:           len(missing) == 0,
		SharedSkillsExists: sharedSkills,
	}, missing, nil
}

func hasDirectory(path string) (bool, error) {
	info, err := statPath(path)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, errs.Wrap("failed to stat", path, err)
	}
	return info.IsDir(), nil
}

func explicitRootError(path string, missing []string) error {
	return fmt.Errorf(
		"%w: %s\nmissing required directories: %s\nexample: export CONTEXT_REPO=%s",
		errs.ErrInvalidContextRepo,
		path,
		strings.Join(missing, ", "),
		path,
	)
}
