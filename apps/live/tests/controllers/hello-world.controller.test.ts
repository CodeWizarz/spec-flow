/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Server as HttpServer } from "node:http";
import express from "express";
import { afterAll, describe, expect, it } from "vitest";
import { registerController } from "@plane/decorators";
import { HelloWorldController } from "@/controllers/hello-world.controller";

function getBaseUrl(server: HttpServer): string {
  const address = server.address();

  if (!address || typeof address === "string") {
    throw new Error("Expected server to be listening on a TCP port");
  }

  return `http://127.0.0.1:${address.port}`;
}

describe("HelloWorldController", () => {
  const app = express();
  const router = express.Router();

  registerController(router, HelloWorldController);
  app.use("/live", router);

  const server = app.listen(0);

  afterAll(async () => {
    await new Promise<void>((resolve, reject) => {
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve();
      });
    });
  });

  it("returns a hello world response", async () => {
    const response = await fetch(`${getBaseUrl(server)}/live/hello-world`);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      message: "Hello, world!",
    });
  });
});
