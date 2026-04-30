clc; clear; close all;

%% -----------------------------
% Load Data
%% -----------------------------
tmp = load('C:\sar_data\sfcw_matrix.mat');
fn = fieldnames(tmp);
raw = tmp.(fn{1});   % load matrix

config = jsondecode(fileread('C:\sar_data\sfcw_config.json'));

%% -----------------------------
% Constants
%% -----------------------------
c = 3e8;

f_start = config.f_start;
f_stop  = config.f_stop;
Nf      = config.n_freq;
Np      = config.n_pos;
dx      = config.dx;

freq = linspace(f_start, f_stop, Nf).';
k = 2*pi*freq/c;

%% -----------------------------
% Fix Data Orientation
%% -----------------------------
% Convert (Np x Nf) → (Nf x Np)
data = raw.';

if size(data,1) ~= Nf
    error('Data dimension mismatch');
end

%% -----------------------------
% Remove Static Clutter
%% -----------------------------
data = data - mean(data, 2);

%% -----------------------------
% Windowing
%% -----------------------------
win_f = hamming(Nf);
win_x = hamming(Np).';

data = data .* (win_f * win_x);

%% -----------------------------
% Imaging Grid
%% -----------------------------
x_aperture = ((0:Np-1) - (Np-1)/2) * dx;

x_img = linspace(-0.5, 0.5, 300);
z_img = linspace(0.5, 4, 300);

[X, Z] = meshgrid(x_img, z_img);
image_bp = zeros(size(X));

%% -----------------------------
% Backprojection (Improved)
%% -----------------------------
R0 = config.target_range;

fprintf('Reconstructing SAR image...\n');

for ix = 1:Np
    xa = x_aperture(ix);
    
    % Normalize signal to reduce streak artifacts
    sig = data(:, ix);
    sig = sig / (max(abs(sig)) + 1e-6);
    
    for i = 1:numel(X)
        R = sqrt((X(i)-xa).^2 + Z(i).^2);
        
        % Phase reference correction
        phase = exp(1j * 2 * k * (R - R0));
        
        % Amplitude compensation
        image_bp(i) = image_bp(i) + sum((sig .* phase) ./ (R.^2));
    end
end

fprintf('Done.\n');

%% -----------------------------
% Normalize
%% -----------------------------
image_bp = abs(image_bp);
image_bp = image_bp / max(image_bp(:));

%% -----------------------------
% Linear Scale Display
%% -----------------------------
figure;
imagesc(x_img, z_img, image_bp);
colormap jet;
colorbar;
xlabel('Cross-range (m)');
ylabel('Range (m)');
title('SAR Image (Linear)');
set(gca,'YDir','normal');

%% -----------------------------
% Log Scale Display (Better)
%% -----------------------------
figure;
imagesc(x_img, z_img, 20*log10(image_bp + 1e-6));
colormap jet;
colorbar;
caxis([-40 0]);
xlabel('Cross-range (m)');
ylabel('Range (m)');
title('SAR Image (Log Scale)');
set(gca,'YDir','normal');
