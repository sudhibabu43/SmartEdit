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

#include "IntegerRatio.h"

using namespace RESAMPLER_OUTER_NAMESPACE::resampler;

// Enough primes to cover the common sample rates.
static const int kPrimes[] = {2,   3,   5,   7,   11,  13,  17,  19,  23,  29,
                              31,  37,  41,  43,  47,  53,  59,  61,  67,  71,
                              73,  79,  83,  89,  97,  101, 103, 107, 109, 113,
                              127, 131, 137, 139, 149, 151, 157, 163, 167, 173,
                              179, 181, 191, 193, 197, 199};

void IntegerRatio::reduce() {
  for (int prime : kPrimes) {
    if (mNumerator < prime || mDenominator < prime) {
      break;
    }

    // Find biggest prime factor for numerator.
    while (true) {
      int top = mNumerator / prime;
      int bottom = mDenominator / prime;
      if ((top >= 1) && (bottom >= 1) &&
          (top * prime == mNumerator) // divided evenly?
          && (bottom * prime == mDenominator)) {
        mNumerator = top;
        mDenominator = bottom;
      } else {
        break;
      }
    }
  }
}
