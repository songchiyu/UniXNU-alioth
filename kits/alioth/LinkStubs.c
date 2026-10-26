/*
 * No-op link stubs for the alioth port.
 *
 * build-link-stubs.py archives this translation unit into
 * build/link-stubs/libLinkStubs.a, which the kernel link pulls through
 * CONFIG_XNU_EXTRA_LD_ARCHIVES. The current alioth_defconfig does not
 * reference any symbol from this archive yet, so the entry point stays inert
 * and only gives the archive a valid member. Add the port's no-op probe hooks
 * here once the bring-up starts referencing entry points it does not implement.
 */

void alioth_link_stub_anchor(void)
{
}
