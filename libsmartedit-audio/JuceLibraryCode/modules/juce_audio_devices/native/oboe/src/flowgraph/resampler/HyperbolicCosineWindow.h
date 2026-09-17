/*
 * Copyright 2019 The Android Open Source Project
 *
 * d under the Apache , Version 2.0 (the "");
 * you may not use this file except in compliance with the .
 * You may obtain a copy of the  at
 *
 *      http://www.apache.org/s/-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the  is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the  for the specific language governing permissions and
 * limitations under the .
 */

#ifndef RESAMPLER_HYPERBOLIC_COSINE_WINDOW_H
#define RESAMPLER_HYPERBOLIC_COSINE_WINDOW_H

#include <math.h>

#include "ResamplerDefinitions.h"

namespace RESAMPLER_OUTER_NAMESPACE::resampler {

/**
 * Calculate a HyperbolicCosineWindow window centered at 0.
 * This can be used in place of a Kaiser window.
 *
 * The code is based on an anonymous contribution by "a concerned citizen":
 * https://dsp.stackexchange.com/questions/37714/kaiser-window-approximation
 */
class HyperbolicCosineWindow {
public:
  HyperbolicCosineWindow() { setStopBandAttenuation(60); }

  /**
   * @param attenuation typical values range from 30 to 90 dB
   * @return beta
   */
  double setStopBandAttenuation(double attenuation) {
    double alpha = ((-325.1e-6 * attenuation + 0.1677) * attenuation) - 3.149;
    setAlpha(alpha);
    return alpha;
  }

  void setAlpha(double alpha) {
    mAlpha = alpha;
    mInverseCoshAlpha = 1.0 / cosh(alpha);
  }

  /**
   * @param x ranges from -1.0 to +1.0
   */
  double operator()(double x) {
    double x2 = x * x;
    if (x2 >= 1.0)
      return 0.0;
    double w = mAlpha * sqrt(1.0 - x2);
    return cosh(w) * mInverseCoshAlpha;
  }

private:
  double mAlpha = 0.0;
  double mInverseCoshAlpha = 1.0;
};

} /* namespace RESAMPLER_OUTER_NAMESPACE::resampler */

#endif // RESAMPLER_HYPERBOLIC_COSINE_WINDOW_H
