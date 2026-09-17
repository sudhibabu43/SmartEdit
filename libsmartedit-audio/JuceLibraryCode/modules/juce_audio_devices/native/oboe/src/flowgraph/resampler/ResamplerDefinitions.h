/*
 * Copyright 2022 The Android Open Source Project
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

// Set flag RESAMPLER_OUTER_NAMESPACE based on whether compiler flag
// __ANDROID_NDK__ is defined. __ANDROID_NDK__ should be defined in oboe
// but not in android.

#ifndef RESAMPLER_OUTER_NAMESPACE
#ifdef __ANDROID_NDK__
#define RESAMPLER_OUTER_NAMESPACE oboe
#else
#define RESAMPLER_OUTER_NAMESPACE aaudio
#endif // __ANDROID_NDK__
#endif // RESAMPLER_OUTER_NAMESPACE
