# Coup expansion strategy findings

These results concern the tested computer policies and opponent fields. They do not establish optimal human play.

1,908,576 scheduled games; 17,960 capped games counted in every win-rate denominator.

## Equal-field confirmation results

Each row compares the two policies selected on earlier screening, averaged equally across five programmed opponent fields. These averages are descriptive.

| Expansion | Players | Policy | Wins / games | Equal-field win rate | Worst field |
| --- | ---: | --- | ---: | ---: | --- |
| inquisitor | 2 | bluff | 6609 / 10000 | 66.09% | skeptical (19.55%) |
| inquisitor | 2 | shield | 4771 / 10000 | 47.71% | bluffing (8.95%) |
| inquisitor | 3 | bluff | 7500 / 15000 | 50.00% | skeptical (16.73%) |
| inquisitor | 3 | shield | 5933 / 15000 | 39.55% | bluffing (10.27%) |
| inquisitor | 4 | bluff | 7987 / 20000 | 39.93% | skeptical (14.07%) |
| inquisitor | 4 | shield | 6931 / 20000 | 34.66% | bluffing (14.30%) |
| inquisitor | 5 | shield | 8093 / 25000 | 32.37% | adaptive (19.82%) |
| inquisitor | 5 | honest | 8093 / 25000 | 32.37% | honest (17.96%) |
| inquisitor | 6 | honest | 10902 / 30000 | 36.34% | honest (16.50%) |
| inquisitor | 6 | shield | 10020 / 30000 | 33.40% | honest (13.65%) |
| inquisitor | 7 | honest | 10027 / 35000 | 28.65% | honest (12.54%) |
| inquisitor | 7 | bluff | 8654 / 35000 | 24.73% | skeptical (8.64%) |
| inquisitor | 8 | honest | 12648 / 40000 | 31.62% | honest (11.61%) |
| inquisitor | 8 | shield | 11722 / 40000 | 29.30% | honest (11.05%) |
| inquisitor | 9 | honest | 11824 / 45000 | 26.28% | mixed (8.81%) |
| inquisitor | 9 | shield | 11902 / 45000 | 26.45% | mixed (9.86%) |
| inquisitor | 10 | honest | 14223 / 50000 | 28.45% | honest (9.18%) |
| inquisitor | 10 | shield | 13578 / 50000 | 27.16% | mixed (9.85%) |
| reformation | 2 | bluff | 6555 / 10000 | 65.55% | skeptical (18.75%) |
| reformation | 2 | shield | 4692 / 10000 | 46.92% | bluffing (9.30%) |
| reformation | 3 | bluff | 7052 / 15000 | 47.01% | skeptical (14.27%) |
| reformation | 3 | converter | 6460 / 15000 | 43.07% | bluffing (30.10%) |
| reformation | 4 | shield | 8067 / 20000 | 40.34% | bluffing (22.18%) |
| reformation | 4 | bluff | 7353 / 20000 | 36.77% | skeptical (12.80%) |
| reformation | 5 | shield | 9137 / 25000 | 36.55% | bluffing (24.82%) |
| reformation | 5 | balanced | 8176 / 25000 | 32.70% | adaptive (21.08%) |
| reformation | 6 | shield | 10746 / 30000 | 35.82% | honest (18.17%) |
| reformation | 6 | honest | 9581 / 30000 | 31.94% | honest (16.00%) |
| reformation | 7 | shield | 10491 / 35000 | 29.97% | bluffing (15.79%) |
| reformation | 7 | information | 9712 / 35000 | 27.75% | honest (14.61%) |
| reformation | 8 | shield | 12533 / 40000 | 31.33% | honest (15.82%) |
| reformation | 8 | balanced | 10869 / 40000 | 27.17% | honest (10.10%) |
| reformation | 9 | information | 11474 / 45000 | 25.50% | adaptive (11.81%) |
| reformation | 9 | shield | 12287 / 45000 | 27.30% | mixed (12.50%) |
| reformation | 10 | shield | 13870 / 50000 | 27.74% | honest (12.18%) |
| reformation | 10 | balanced | 12232 / 50000 | 24.46% | honest (8.35%) |
| combined | 2 | bluff | 6619 / 10000 | 66.19% | skeptical (18.90%) |
| combined | 2 | shield | 4696 / 10000 | 46.96% | bluffing (9.25%) |
| combined | 3 | shield | 7133 / 15000 | 47.55% | bluffing (27.93%) |
| combined | 3 | bluff | 7238 / 15000 | 48.25% | skeptical (16.17%) |
| combined | 4 | bluff | 7764 / 20000 | 38.82% | skeptical (13.15%) |
| combined | 4 | shield | 8291 / 20000 | 41.45% | bluffing (21.48%) |
| combined | 5 | shield | 9483 / 25000 | 37.93% | bluffing (24.02%) |
| combined | 5 | balanced | 8153 / 25000 | 32.61% | adaptive (20.24%) |
| combined | 6 | shield | 10960 / 30000 | 36.53% | honest (21.15%) |
| combined | 6 | honest | 9257 / 30000 | 30.86% | honest (16.05%) |
| combined | 7 | balanced | 9621 / 35000 | 27.49% | adaptive (13.77%) |
| combined | 7 | shield | 10737 / 35000 | 30.68% | bluffing (15.10%) |
| combined | 8 | shield | 12643 / 40000 | 31.61% | mixed (17.20%) |
| combined | 8 | converter | 11100 / 40000 | 27.75% | honest (11.31%) |
| combined | 9 | shield | 12545 / 45000 | 27.88% | mixed (12.08%) |
| combined | 9 | balanced | 12112 / 45000 | 26.92% | adaptive (11.31%) |
| combined | 10 | shield | 13817 / 50000 | 27.63% | mixed (12.33%) |
| combined | 10 | balanced | 12161 / 50000 | 24.32% | adaptive (9.28%) |

## Paired evidence

The 135 confirmation contrasts use matched complete rotation blocks. Normal simultaneous intervals are approximate; Hoeffding intervals are conservative. A positive bound supports a modeled advantage; a lower bound above two percentage points supports a practical advantage under that method.

| Expansion | Players | Field | First vs second | Difference | Approximate interval | Conservative interval |
| --- | ---: | --- | --- | ---: | --- | --- |
| inquisitor | 2 | honest | bluff vs shield | +34.85 pp | +31.65 to +38.05 pp | +21.74 to +47.96 pp |
| inquisitor | 2 | bluffing | bluff vs shield | +41.05 pp | +38.89 to +43.21 pp | +27.94 to +54.16 pp |
| inquisitor | 2 | skeptical | bluff vs shield | -50.20 pp | -53.94 to -46.46 pp | -63.31 to -37.09 pp |
| inquisitor | 2 | adaptive | bluff vs shield | +38.10 pp | +34.33 to +41.87 pp | +24.99 to +51.21 pp |
| inquisitor | 2 | mixed | bluff vs shield | +28.10 pp | +23.36 to +32.84 pp | +14.99 to +41.21 pp |
| inquisitor | 3 | honest | bluff vs shield | +32.23 pp | +28.36 to +36.10 pp | +19.12 to +45.34 pp |
| inquisitor | 3 | bluffing | bluff vs shield | +23.07 pp | +21.25 to +24.88 pp | +9.96 to +36.18 pp |
| inquisitor | 3 | skeptical | bluff vs shield | -59.57 pp | -62.92 to -56.21 pp | -72.68 to -46.46 pp |
| inquisitor | 3 | adaptive | bluff vs shield | +33.53 pp | +29.43 to +37.64 pp | +20.42 to +46.64 pp |
| inquisitor | 3 | mixed | bluff vs shield | +22.97 pp | +18.25 to +27.69 pp | +9.86 to +36.08 pp |
| inquisitor | 4 | honest | bluff vs shield | +31.10 pp | +27.37 to +34.83 pp | +17.99 to +44.21 pp |
| inquisitor | 4 | bluffing | bluff vs shield | +10.70 pp | +8.58 to +12.82 pp | -2.41 to +23.81 pp |
| inquisitor | 4 | skeptical | bluff vs shield | -63.42 pp | -66.26 to -60.59 pp | -76.54 to -50.31 pp |
| inquisitor | 4 | adaptive | bluff vs shield | +25.87 pp | +22.32 to +29.43 pp | +12.76 to +38.99 pp |
| inquisitor | 4 | mixed | bluff vs shield | +22.15 pp | +18.46 to +25.84 pp | +9.04 to +35.26 pp |
| inquisitor | 5 | honest | shield vs honest | +3.62 pp | +1.59 to +5.65 pp | -9.49 to +16.73 pp |
| inquisitor | 5 | bluffing | shield vs honest | +2.00 pp | +0.82 to +3.18 pp | -11.11 to +15.11 pp |
| inquisitor | 5 | skeptical | shield vs honest | -7.64 pp | -9.20 to -6.08 pp | -20.75 to +5.47 pp |
| inquisitor | 5 | adaptive | shield vs honest | +1.30 pp | -0.93 to +3.53 pp | -11.81 to +14.41 pp |
| inquisitor | 5 | mixed | shield vs honest | +0.72 pp | -1.24 to +2.68 pp | -12.39 to +13.83 pp |
| inquisitor | 6 | honest | honest vs shield | +2.85 pp | +1.08 to +4.62 pp | -10.26 to +15.96 pp |
| inquisitor | 6 | bluffing | honest vs shield | -0.02 pp | -1.33 to +1.30 pp | -13.13 to +13.09 pp |
| inquisitor | 6 | skeptical | honest vs shield | +7.92 pp | +6.50 to +9.33 pp | -5.19 to +21.03 pp |
| inquisitor | 6 | adaptive | honest vs shield | +2.17 pp | +0.11 to +4.22 pp | -10.94 to +15.28 pp |
| inquisitor | 6 | mixed | honest vs shield | +1.78 pp | -0.09 to +3.66 pp | -11.33 to +14.89 pp |
| inquisitor | 7 | honest | honest vs bluff | -23.17 pp | -26.06 to -20.28 pp | -36.28 to -10.06 pp |
| inquisitor | 7 | bluffing | honest vs bluff | +0.94 pp | -1.10 to +2.99 pp | -12.17 to +14.05 pp |
| inquisitor | 7 | skeptical | honest vs bluff | +77.53 pp | +75.74 to +79.32 pp | +64.42 to +90.64 pp |
| inquisitor | 7 | adaptive | honest vs bluff | -21.07 pp | -23.66 to -18.48 pp | -34.18 to -7.96 pp |
| inquisitor | 7 | mixed | honest vs bluff | -14.61 pp | -17.05 to -12.18 pp | -27.72 to -1.50 pp |
| inquisitor | 8 | honest | honest vs shield | +0.56 pp | -1.05 to +2.17 pp | -12.55 to +13.67 pp |
| inquisitor | 8 | bluffing | honest vs shield | -2.11 pp | -3.46 to -0.77 pp | -15.22 to +11.00 pp |
| inquisitor | 8 | skeptical | honest vs shield | +8.71 pp | +7.45 to +9.97 pp | -4.40 to +21.82 pp |
| inquisitor | 8 | adaptive | honest vs shield | +2.73 pp | +0.96 to +4.49 pp | -10.39 to +15.84 pp |
| inquisitor | 8 | mixed | honest vs shield | +1.69 pp | +0.16 to +3.22 pp | -11.42 to +14.80 pp |
| inquisitor | 9 | honest | honest vs shield | -5.31 pp | -6.90 to -3.72 pp | -18.42 to +7.80 pp |
| inquisitor | 9 | bluffing | honest vs shield | -4.92 pp | -6.11 to -3.73 pp | -18.03 to +8.19 pp |
| inquisitor | 9 | skeptical | honest vs shield | +9.41 pp | +8.09 to +10.73 pp | -3.70 to +22.52 pp |
| inquisitor | 9 | adaptive | honest vs shield | +1.00 pp | -0.53 to +2.53 pp | -12.11 to +14.11 pp |
| inquisitor | 9 | mixed | honest vs shield | -1.04 pp | -2.42 to +0.33 pp | -14.15 to +12.07 pp |
| inquisitor | 10 | honest | honest vs shield | -1.33 pp | -2.75 to +0.09 pp | -14.44 to +11.78 pp |
| inquisitor | 10 | bluffing | honest vs shield | -5.75 pp | -7.17 to -4.33 pp | -18.86 to +7.36 pp |
| inquisitor | 10 | skeptical | honest vs shield | +10.16 pp | +8.86 to +11.46 pp | -2.95 to +23.27 pp |
| inquisitor | 10 | adaptive | honest vs shield | +2.73 pp | +1.16 to +4.30 pp | -10.38 to +15.84 pp |
| inquisitor | 10 | mixed | honest vs shield | +0.64 pp | -0.64 to +1.92 pp | -12.47 to +13.75 pp |
| reformation | 2 | honest | bluff vs shield | +35.35 pp | +32.11 to +38.59 pp | +22.24 to +48.46 pp |
| reformation | 2 | bluffing | bluff vs shield | +40.70 pp | +38.51 to +42.89 pp | +27.59 to +53.81 pp |
| reformation | 2 | skeptical | bluff vs shield | -47.80 pp | -51.59 to -44.01 pp | -60.91 to -34.69 pp |
| reformation | 2 | adaptive | bluff vs shield | +37.75 pp | +34.04 to +41.46 pp | +24.64 to +50.86 pp |
| reformation | 2 | mixed | bluff vs shield | +27.15 pp | +22.34 to +31.96 pp | +14.04 to +40.26 pp |
| reformation | 3 | honest | bluff vs converter | +17.97 pp | +13.48 to +22.45 pp | +4.86 to +31.08 pp |
| reformation | 3 | bluffing | bluff vs converter | +3.23 pp | +0.53 to +5.93 pp | -9.88 to +16.34 pp |
| reformation | 3 | skeptical | bluff vs converter | -43.90 pp | -47.11 to -40.69 pp | -57.01 to -30.79 pp |
| reformation | 3 | adaptive | bluff vs converter | +23.83 pp | +19.33 to +28.33 pp | +10.72 to +36.94 pp |
| reformation | 3 | mixed | bluff vs converter | +18.60 pp | +14.09 to +23.11 pp | +5.49 to +31.71 pp |
| reformation | 4 | honest | shield vs bluff | -21.30 pp | -25.19 to -17.41 pp | -34.41 to -8.19 pp |
| reformation | 4 | bluffing | shield vs bluff | -2.83 pp | -5.07 to -0.58 pp | -15.94 to +10.29 pp |
| reformation | 4 | skeptical | shield vs bluff | +61.98 pp | +59.05 to +64.90 pp | +48.86 to +75.09 pp |
| reformation | 4 | adaptive | shield vs bluff | -13.12 pp | -16.90 to -9.35 pp | -26.24 to -0.01 pp |
| reformation | 4 | mixed | shield vs bluff | -6.88 pp | -10.71 to -3.04 pp | -19.99 to +6.24 pp |
| reformation | 5 | honest | shield vs balanced | +5.74 pp | +3.18 to +8.30 pp | -7.37 to +18.85 pp |
| reformation | 5 | bluffing | shield vs balanced | -4.18 pp | -6.63 to -1.73 pp | -17.29 to +8.93 pp |
| reformation | 5 | skeptical | shield vs balanced | +5.26 pp | +2.64 to +7.88 pp | -7.85 to +18.37 pp |
| reformation | 5 | adaptive | shield vs balanced | +7.62 pp | +4.88 to +10.36 pp | -5.49 to +20.73 pp |
| reformation | 5 | mixed | shield vs balanced | +4.78 pp | +2.10 to +7.46 pp | -8.33 to +17.89 pp |
| reformation | 6 | honest | shield vs honest | +2.17 pp | +0.07 to +4.26 pp | -10.94 to +15.28 pp |
| reformation | 6 | bluffing | shield vs honest | +9.63 pp | +7.27 to +12.00 pp | -3.48 to +22.74 pp |
| reformation | 6 | skeptical | shield vs honest | -6.93 pp | -8.64 to -5.22 pp | -20.04 to +6.18 pp |
| reformation | 6 | adaptive | shield vs honest | +6.67 pp | +4.37 to +8.97 pp | -6.44 to +19.78 pp |
| reformation | 6 | mixed | shield vs honest | +7.88 pp | +5.57 to +10.20 pp | -5.23 to +20.99 pp |
| reformation | 7 | honest | shield vs information | +7.57 pp | +5.49 to +9.65 pp | -5.54 to +20.68 pp |
| reformation | 7 | bluffing | shield vs information | -3.17 pp | -5.05 to -1.30 pp | -16.28 to +9.94 pp |
| reformation | 7 | skeptical | shield vs information | -1.66 pp | -3.84 to +0.53 pp | -14.77 to +11.45 pp |
| reformation | 7 | adaptive | shield vs information | +5.07 pp | +2.90 to +7.24 pp | -8.04 to +18.18 pp |
| reformation | 7 | mixed | shield vs information | +3.31 pp | +1.33 to +5.29 pp | -9.80 to +16.42 pp |
| reformation | 8 | honest | shield vs balanced | +5.73 pp | +4.04 to +7.41 pp | -7.39 to +18.84 pp |
| reformation | 8 | bluffing | shield vs balanced | -3.88 pp | -6.04 to -1.71 pp | -16.99 to +9.24 pp |
| reformation | 8 | skeptical | shield vs balanced | +7.44 pp | +5.21 to +9.67 pp | -5.67 to +20.55 pp |
| reformation | 8 | adaptive | shield vs balanced | +7.83 pp | +5.92 to +9.73 pp | -5.29 to +20.94 pp |
| reformation | 8 | mixed | shield vs balanced | +3.69 pp | +1.81 to +5.56 pp | -9.42 to +16.80 pp |
| reformation | 9 | honest | information vs shield | -5.93 pp | -7.72 to -4.15 pp | -19.04 to +7.18 pp |
| reformation | 9 | bluffing | information vs shield | +1.54 pp | -0.17 to +3.26 pp | -11.57 to +14.65 pp |
| reformation | 9 | skeptical | information vs shield | +0.00 pp | -1.98 to +1.98 pp | -13.11 to +13.11 pp |
| reformation | 9 | adaptive | information vs shield | -4.42 pp | -6.15 to -2.69 pp | -17.53 to +8.69 pp |
| reformation | 9 | mixed | information vs shield | -0.22 pp | -1.80 to +1.36 pp | -13.33 to +12.89 pp |
| reformation | 10 | honest | shield vs balanced | +3.83 pp | +2.48 to +5.18 pp | -9.28 to +16.94 pp |
| reformation | 10 | bluffing | shield vs balanced | -5.15 pp | -6.99 to -3.31 pp | -18.26 to +7.96 pp |
| reformation | 10 | skeptical | shield vs balanced | +9.31 pp | +7.31 to +11.31 pp | -3.80 to +22.42 pp |
| reformation | 10 | adaptive | shield vs balanced | +6.83 pp | +5.17 to +8.49 pp | -6.28 to +19.94 pp |
| reformation | 10 | mixed | shield vs balanced | +1.56 pp | -0.10 to +3.22 pp | -11.55 to +14.67 pp |
| combined | 2 | honest | bluff vs shield | +36.65 pp | +33.52 to +39.78 pp | +23.54 to +49.76 pp |
| combined | 2 | bluffing | bluff vs shield | +40.75 pp | +38.56 to +42.94 pp | +27.64 to +53.86 pp |
| combined | 2 | skeptical | bluff vs shield | -47.90 pp | -51.75 to -44.05 pp | -61.01 to -34.79 pp |
| combined | 2 | adaptive | bluff vs shield | +39.60 pp | +35.87 to +43.33 pp | +26.49 to +52.71 pp |
| combined | 2 | mixed | bluff vs shield | +27.05 pp | +22.24 to +31.86 pp | +13.94 to +40.16 pp |
| combined | 3 | honest | shield vs bluff | -22.90 pp | -27.16 to -18.64 pp | -36.01 to -9.79 pp |
| combined | 3 | bluffing | shield vs bluff | -5.40 pp | -7.89 to -2.91 pp | -18.51 to +7.71 pp |
| combined | 3 | skeptical | shield vs bluff | +60.03 pp | +56.70 to +63.37 pp | +46.92 to +73.14 pp |
| combined | 3 | adaptive | shield vs bluff | -21.57 pp | -25.95 to -17.18 pp | -34.68 to -8.46 pp |
| combined | 3 | mixed | shield vs bluff | -13.67 pp | -18.24 to -9.10 pp | -26.78 to -0.56 pp |
| combined | 4 | honest | bluff vs shield | +20.97 pp | +17.10 to +24.85 pp | +7.86 to +34.09 pp |
| combined | 4 | bluffing | bluff vs shield | +3.52 pp | +1.18 to +5.87 pp | -9.59 to +16.64 pp |
| combined | 4 | skeptical | bluff vs shield | -65.05 pp | -67.85 to -62.25 pp | -78.16 to -51.94 pp |
| combined | 4 | adaptive | bluff vs shield | +15.30 pp | +11.45 to +19.15 pp | +2.19 to +28.41 pp |
| combined | 4 | mixed | bluff vs shield | +12.07 pp | +8.16 to +15.99 pp | -1.04 to +25.19 pp |
| combined | 5 | honest | shield vs balanced | +3.50 pp | +0.71 to +6.29 pp | -9.61 to +16.61 pp |
| combined | 5 | bluffing | shield vs balanced | -3.90 pp | -6.51 to -1.29 pp | -17.01 to +9.21 pp |
| combined | 5 | skeptical | shield vs balanced | +11.98 pp | +9.47 to +14.49 pp | -1.13 to +25.09 pp |
| combined | 5 | adaptive | shield vs balanced | +8.70 pp | +5.90 to +11.50 pp | -4.41 to +21.81 pp |
| combined | 5 | mixed | shield vs balanced | +6.32 pp | +3.62 to +9.02 pp | -6.79 to +19.43 pp |
| combined | 6 | honest | shield vs honest | +5.10 pp | +2.97 to +7.23 pp | -8.01 to +18.21 pp |
| combined | 6 | bluffing | shield vs honest | +11.07 pp | +8.83 to +13.30 pp | -2.04 to +24.18 pp |
| combined | 6 | skeptical | shield vs honest | -5.58 pp | -7.24 to -3.93 pp | -18.69 to +7.53 pp |
| combined | 6 | adaptive | shield vs honest | +9.93 pp | +7.72 to +12.15 pp | -3.18 to +23.04 pp |
| combined | 6 | mixed | shield vs honest | +7.87 pp | +5.70 to +10.03 pp | -5.24 to +20.98 pp |
| combined | 7 | honest | balanced vs shield | -2.53 pp | -4.88 to -0.18 pp | -15.64 to +10.58 pp |
| combined | 7 | bluffing | balanced vs shield | +6.30 pp | +4.28 to +8.32 pp | -6.81 to +19.41 pp |
| combined | 7 | skeptical | balanced vs shield | -13.07 pp | -15.18 to -10.96 pp | -26.18 to +0.04 pp |
| combined | 7 | adaptive | balanced vs shield | -4.33 pp | -6.44 to -2.21 pp | -17.44 to +8.78 pp |
| combined | 7 | mixed | balanced vs shield | -2.31 pp | -4.38 to -0.25 pp | -15.42 to +10.80 pp |
| combined | 8 | honest | shield vs converter | +6.16 pp | +4.44 to +7.89 pp | -6.95 to +19.27 pp |
| combined | 8 | bluffing | shield vs converter | -3.24 pp | -5.09 to -1.38 pp | -16.35 to +9.87 pp |
| combined | 8 | skeptical | shield vs converter | +12.19 pp | +10.33 to +14.05 pp | -0.92 to +25.30 pp |
| combined | 8 | adaptive | shield vs converter | +2.08 pp | -0.04 to +4.19 pp | -11.04 to +15.19 pp |
| combined | 8 | mixed | shield vs converter | +2.10 pp | +0.20 to +4.00 pp | -11.01 to +15.21 pp |
| combined | 9 | honest | shield vs balanced | +1.22 pp | -0.80 to +3.24 pp | -11.89 to +14.33 pp |
| combined | 9 | bluffing | shield vs balanced | -14.23 pp | -16.26 to -12.21 pp | -27.34 to -1.12 pp |
| combined | 9 | skeptical | shield vs balanced | +14.00 pp | +12.01 to +15.99 pp | +0.89 to +27.11 pp |
| combined | 9 | adaptive | shield vs balanced | +3.08 pp | +1.37 to +4.78 pp | -10.03 to +16.19 pp |
| combined | 9 | mixed | shield vs balanced | +0.74 pp | -1.01 to +2.50 pp | -12.37 to +13.85 pp |
| combined | 10 | honest | shield vs balanced | +2.31 pp | +0.66 to +3.96 pp | -10.80 to +15.42 pp |
| combined | 10 | bluffing | shield vs balanced | -6.15 pp | -8.15 to -4.15 pp | -19.26 to +6.96 pp |
| combined | 10 | skeptical | shield vs balanced | +15.14 pp | +13.31 to +16.97 pp | +2.03 to +28.25 pp |
| combined | 10 | adaptive | shield vs balanced | +3.92 pp | +2.35 to +5.49 pp | -9.19 to +17.03 pp |
| combined | 10 | mixed | shield vs balanced | +1.34 pp | -0.23 to +2.91 pp | -11.77 to +14.45 pp |

## Targeted counters

Targets came from screening; counters were selected on separate search games and tested on fresh games against copies of the target. Each paired reference is target self-play.

| Expansion | Players | Counter vs target | Counter win rate | Difference | Conservative interval |
| --- | ---: | --- | ---: | ---: | --- |
| inquisitor | 2 | skeptic vs bluff | 82.20% | +32.20 pp | +21.73 to +42.67 pp |
| inquisitor | 6 | bluff vs honest | 21.92% | +6.23 pp | -4.24 to +16.70 pp |
| reformation | 4 | bluff vs shield | 37.55% | +13.70 pp | +3.23 to +24.17 pp |
| reformation | 10 | bluff vs shield | 13.72% | +3.30 pp | -7.17 to +13.77 pp |
| combined | 4 | skeptic vs bluff | 41.25% | +16.25 pp | +5.78 to +26.72 pp |
| combined | 10 | bluff vs shield | 20.15% | +10.34 pp | -0.13 to +20.81 pp |

## Scope

The protocol and execution sources were frozen in a local hashed snapshot before outcomes. This is not independent timestamp registration. The model omits negotiation, persuasion and cross-game adaptation. Opponent fields are scenarios, not an estimate of human populations. Public mechanism counters are descriptive. The two confirmed policies per player count cannot establish superiority over every screened or untested strategy.
