% Optional numerical installation smoke test, not a calibrated scientific case.
% octave-cli --no-gui --no-window-system --no-history windows_smoke.m <source>
args = argv();
assert(numel(args) == 1, 'Pass the inner MARRMoT source directory');
addpath(genpath(args{1}));
pkg load optim;
pkg load statistics;
m = m_01_collie1_1p_1s();
assert(m.numParams == 1 && m.numStores == 1);
m.theta = [100];
m.S0 = [0];
m.delta_t = 1;
m.solver_opts.resnorm_tolerance = 0.1;
m.solver_opts.resnorm_maxiter = 6;
m.input_climate = [[120; 0; 4; 0; 8; 0; 0; 3; 0; 1], 2 * ones(10, 1), 10 * ones(10, 1)];
[fluxOutput, fluxInternal, storeInternal, waterBalance] = m.get_output();
assert(numel(fluxOutput.Q) == 10);
assert(all(isfinite(fluxOutput.Q)) && all(fluxOutput.Q >= -1e-10));
assert(all(isfinite(fluxOutput.Ea)) && all(fluxOutput.Ea >= -1e-10));
assert(all(isfinite(m.stores(:))));
assert(isfinite(waterBalance) && abs(waterBalance) < 1e-6);
fprintf('MARRMOT_SMOKE_OK octave=%s timesteps=%d sumQ=%.9f sumEa=%.9f finalS=%.9f waterBalance=%.12g\n', ...
        version(), numel(fluxOutput.Q), sum(fluxOutput.Q), sum(fluxOutput.Ea), m.stores(end), waterBalance);
