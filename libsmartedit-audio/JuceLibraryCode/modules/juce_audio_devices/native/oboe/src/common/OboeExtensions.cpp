/*
 * Copyright (C) 2022 The Android Open Source Project
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

#include "oboe/OboeExtensions.h"
#include "aaudio/AAudioExtensions.h"

using namespace oboe;

bool OboeExtensions::isMMapSupported() {
  return AAudioExtensions::getInstance().isMMapSupported();
}

bool OboeExtensions::isMMapEnabled() {
  return AAudioExtensions::getInstance().isMMapEnabled();
}

int32_t OboeExtensions::setMMapEnabled(bool enabled) {
  return AAudioExtensions::getInstance().setMMapEnabled(enabled);
}

bool OboeExtensions::isMMapUsed(oboe::AudioStream *oboeStream) {
  return AAudioExtensions::getInstance().isMMapUsed(oboeStream);
}
