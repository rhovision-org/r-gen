import Lake
open Lake DSL

package rgen

@[default_target]
lean_lib RGen

lean_exe emit where
  root := `RGen.Emit
