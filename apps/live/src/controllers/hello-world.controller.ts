/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Request, Response } from "express";
import { Controller, Get } from "@plane/decorators";

@Controller("/hello-world")
export class HelloWorldController {
  @Get("/")
  async getHelloWorld(_req: Request, res: Response) {
    res.status(200).json({
      message: "Hello, world!",
    });
  }
}
