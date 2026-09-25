# Wave 1 Plugin SDK contract

Status: Alpha

A WestQuant plugin may implement any subset of five interfaces:

1. FrontendAdapter: native object <-> WQIR representation.
2. TransformationProvider: enumerate and apply representation transformations.
3. CompilerAdapter: lower a representation toward a target.
4. EvaluatorAdapter: score a representation without executing it on hardware.
5. RuntimeAdapter: execute a representation on simulator or QPU.

All search events must be serializable as RepGraph edges. Failed transformations
are first-class outcomes and must not be silently dropped.

The core must remain usable with deterministic search when WQT20 is absent.
