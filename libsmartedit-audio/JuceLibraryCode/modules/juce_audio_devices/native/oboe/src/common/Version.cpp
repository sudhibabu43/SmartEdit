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
#include "oboe/Version.h"

namespace oboe {

// This variable enables the version information to be read from the resulting
// binary e.g. by running `objdump -s --section=.data <binary>` Please do not
// optimize or change in any way.
char kVersionText[] = "OboeVersion" OBOE_VERSION_TEXT;

const char *getVersionText() { return kVersionText; }
} // namespace oboe
