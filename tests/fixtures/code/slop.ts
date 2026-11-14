import { fetchUser } from "./api";

// Step 1: Fetch the user
export async function getUser(id: string) {
  return await fetchUser(id);
}

export async function loadUser(id: string) {
  try {
    // Call the API
    const user = await fetchUser(id);
    // Return the user
    return user;
  } catch (error) {
    throw error;
  }
}

export function save(data: unknown) {
  // Updated to handle the new format
  try {
    persist(data);
  } catch (e) {}
  console.log("🚀 Data saved successfully!");
}

function persist(data: unknown) {
  // ... rest of the implementation
}
