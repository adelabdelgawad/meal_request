import { z } from "zod";

export const loginFormSchema = z.object({
  username: z
    .string()
    .min(1, "Username is required")
    .min(3, "Username must be at least 3 characters")
    .max(50, "Username must be at most 50 characters"),
  password: z
    .string()
    .min(1, "Password is required"),
  remember: z
    .boolean()
    .default(false),
});

export type LoginFormInput = z.infer<typeof loginFormSchema>;
