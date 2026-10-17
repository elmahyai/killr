/* readPNG's libpng calls, loaded with ctypes.

libpng reports errors with longjmp. A callback that returns into the
interpreter lets that jump land in Python, so the setjmp stays in this
function.
*/

#include <png.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define R_RGB(r, g, b) ((uint32_t)(r) | ((uint32_t)(g) << 8) | ((uint32_t)(b) << 16) | 0xFF000000u)
#define R_RGBA(r, g, b, a) ((uint32_t)(r) | ((uint32_t)(g) << 8) | ((uint32_t)(b) << 16) | ((uint32_t)(a) << 24))
#define RX_swap32(X) (X) = (((unsigned int)(X)) >> 24) | ((((unsigned int)(X)) >> 8) & 0xff00u) | (((unsigned int)(X)) << 24) | ((((unsigned int)(X)) & 0xff00u) << 8)

typedef struct read_job {
    FILE *f;
    int ptr, len;
    const unsigned char *data;
    char error[1024];
    char warning[2048];
    size_t warning_used;
    png_bytepp rows;
    unsigned char *image;
} read_job_t;

typedef struct readpng_result {
    double *samples;
    int *native_pixels;
    char **text_keys;
    char **text_vals;
    int *text_key_na;
    int *text_val_na;
    double gamma;
    double dpi_x;
    double dpi_y;
    double asp;
    int ok;
    int height;
    int width;
    int planes;
    int native_mode;
    int n_samples;
    int channels;
    int has_info;
    int info_width;
    int info_height;
    int info_bit_depth;
    int color_is_int;
    int color_int;
    int has_gamma;
    int has_dpi;
    int has_asp;
    int ntext;
    char error[1024];
    char warning[2048];
    char color_type[64];
} readpng_result;

static void add_warning(read_job_t *rj, const char *text) {
    size_t n = strlen(text);
    size_t room;
    if (rj->warning_used >= sizeof rj->warning)
        return;
    room = sizeof rj->warning - rj->warning_used - 1;
    if (n > room)
        n = room;
    memcpy(rj->warning + rj->warning_used, text, n);
    rj->warning_used += n;
    rj->warning[rj->warning_used] = '\0';
}

static void user_error_fn(png_structp png_ptr, png_const_charp error_msg) {
    read_job_t *rj = (read_job_t *)png_get_error_ptr(png_ptr);
    snprintf(rj->error, sizeof rj->error, "libpng error: %s", error_msg ? error_msg : "");
    if (rj->f) {
        fclose(rj->f);
        rj->f = NULL;
    }
    png_longjmp(png_ptr, 1);
}

static void user_warning_fn(png_structp png_ptr, png_const_charp warning_msg) {
    read_job_t *rj = (read_job_t *)png_get_error_ptr(png_ptr);
    char line[512];
    snprintf(line, sizeof line, "libpng warning: %s\n", warning_msg ? warning_msg : "");
    add_warning(rj, line);
}

static void user_read_data(png_structp png_ptr, png_bytep data, png_size_t length) {
    read_job_t *rj = (read_job_t *)png_get_io_ptr(png_ptr);
    png_size_t to_read = length;
    if (to_read > (png_size_t)(rj->len - rj->ptr))
        to_read = (png_size_t)(rj->len - rj->ptr);
    if (to_read > 0) {
        memcpy(data, rj->data + rj->ptr, to_read);
        rj->ptr += (int)to_read;
    }
    if (to_read < length)
        memset(data + to_read, 0, length - to_read);
}

static char *dup_or_null(const char *text) {
    size_t n;
    char *copy;
    if (!text)
        return NULL;
    n = strlen(text);
    copy = (char *)malloc(n + 1);
    if (!copy)
        return NULL;
    memcpy(copy, text, n + 1);
    return copy;
}

void readpng_free(readpng_result *out) {
    int i;
    if (!out)
        return;
    free(out->samples);
    free(out->native_pixels);
    out->samples = NULL;
    out->native_pixels = NULL;
    if (out->text_keys) {
        for (i = 0; i < out->ntext; i++)
            free(out->text_keys[i]);
        free(out->text_keys);
        out->text_keys = NULL;
    }
    if (out->text_vals) {
        for (i = 0; i < out->ntext; i++)
            free(out->text_vals[i]);
        free(out->text_vals);
        out->text_vals = NULL;
    }
    free(out->text_key_na);
    free(out->text_val_na);
    out->text_key_na = NULL;
    out->text_val_na = NULL;
}

static void fail(readpng_result *out, const char *message) {
    snprintf(out->error, sizeof out->error, "%s", message);
    out->ok = 0;
}

int readpng_read(const char *path, const unsigned char *raw, int raw_len,
                 int native, int info, readpng_result *out) {
    read_job_t rj;
    png_structp png_ptr;
    png_infop info_ptr;
    volatile FILE *file = NULL;
    volatile png_structp png_volatile = NULL;
    volatile png_infop info_volatile = NULL;
    unsigned char header[8];
    int from_file;

    memset(out, 0, sizeof *out);
    memset(&rj, 0, sizeof rj);
    from_file = path != NULL;
    if (!from_file && raw == NULL && raw_len != 0) {
        fail(out, "invalid filename");
        return 0;
    }
    if (from_file) {
        FILE *opened = fopen(path, "rb");
        if (!opened) {
            snprintf(out->error, sizeof out->error, "unable to open %s", path);
            return 0;
        }
        memset(header, 0, sizeof header);
        if (fread(header, 1, 8, opened) < 1 || png_sig_cmp(header, 0, 8)) {
            fclose(opened);
            fail(out, "file is not in PNG format");
            return 0;
        }
        file = opened;
        rj.f = opened;
    } else {
        rj.data = raw;
        rj.len = raw_len < 0 ? 0 : raw_len;
        rj.ptr = 0;
        rj.f = NULL;
    }

    png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, &rj, user_error_fn, user_warning_fn);
    if (!png_ptr) {
        if (file)
            fclose((FILE *)file);
        fail(out, "unable to initialize libpng");
        return 0;
    }
    png_volatile = png_ptr;
    info_ptr = png_create_info_struct(png_ptr);
    if (!info_ptr) {
        if (file)
            fclose((FILE *)file);
        png_destroy_read_struct(&png_ptr, NULL, NULL);
        fail(out, "unable to initialize libpng");
        return 0;
    }
    info_volatile = info_ptr;

    if (setjmp(png_jmpbuf(png_ptr))) {
        png_structp dead = (png_structp)png_volatile;
        png_infop dead_info = (png_infop)info_volatile;
        free(rj.rows);
        free(rj.image);
        rj.rows = NULL;
        rj.image = NULL;
        if (dead)
            png_destroy_read_struct(&dead, dead_info ? &dead_info : NULL, NULL);
        if (rj.error[0])
            snprintf(out->error, sizeof out->error, "%s", rj.error);
        else
            fail(out, "libpng error: ");
        if (rj.warning_used)
            snprintf(out->warning, sizeof out->warning, "%s", rj.warning);
        readpng_free(out);
        out->ok = 0;
        return 0;
    }

    if (from_file) {
        png_init_io(png_ptr, rj.f);
        png_set_sig_bytes(png_ptr, 8);
    } else {
        png_set_read_fn(png_ptr, &rj, user_read_data);
    }

    png_read_info(png_ptr, info_ptr);
    {
        png_uint_32 width, height;
        png_bytepp row_pointers;
        unsigned char *img_memory;
        int bit_depth, color_type, interlace_type, compression_type, filter_method, rowbytes;
        int need_swap = 0;
        int y;

        png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type,
                     &interlace_type, &compression_type, &filter_method);
        rowbytes = (int)png_get_rowbytes(png_ptr, info_ptr);
        out->info_width = (int)width;
        out->info_height = (int)height;
        out->info_bit_depth = bit_depth;

        if (info) {
            double gamma = 0;
            png_uint_32 rx = 0, ry = 0;
            int unit = 0;
            int num_text = 0;
            png_textp text_ptr = NULL;
            out->has_info = 1;
            switch (color_type) {
            case PNG_COLOR_TYPE_GRAY:
                snprintf(out->color_type, sizeof out->color_type, "gray");
                break;
            case PNG_COLOR_TYPE_GRAY_ALPHA:
                snprintf(out->color_type, sizeof out->color_type, "gray + alpha");
                break;
            case PNG_COLOR_TYPE_PALETTE:
                snprintf(out->color_type, sizeof out->color_type, "palette");
                break;
            case PNG_COLOR_TYPE_RGB:
                snprintf(out->color_type, sizeof out->color_type, "RGB");
                break;
            case PNG_COLOR_TYPE_RGB_ALPHA:
                snprintf(out->color_type, sizeof out->color_type, "RGBA");
                break;
            default:
                out->color_is_int = 1;
                out->color_int = color_type;
                break;
            }
            if (png_get_gAMA(png_ptr, info_ptr, &gamma)) {
                out->has_gamma = 1;
                out->gamma = gamma;
            }
#ifdef PNG_pHYs_SUPPORTED
            if (png_get_pHYs(png_ptr, info_ptr, &rx, &ry, &unit)) {
                if (unit == PNG_RESOLUTION_METER) {
                    out->has_dpi = 1;
                    out->dpi_x = ((double)rx) / 39.37008;
                    out->dpi_y = ((double)ry) / 39.37008;
                } else if (unit == PNG_RESOLUTION_UNKNOWN) {
                    out->has_asp = 1;
                    out->asp = (double)(ry == 0 ? 0 : (rx / ry));
                }
            }
            if (png_get_text(png_ptr, info_ptr, &text_ptr, &num_text) && num_text > 0) {
                int i;
                out->ntext = num_text;
                out->text_keys = (char **)calloc((size_t)num_text, sizeof(char *));
                out->text_vals = (char **)calloc((size_t)num_text, sizeof(char *));
                out->text_key_na = (int *)calloc((size_t)num_text, sizeof(int));
                out->text_val_na = (int *)calloc((size_t)num_text, sizeof(int));
                if (!out->text_keys || !out->text_vals || !out->text_key_na || !out->text_val_na) {
                    png_error(png_ptr, "out of memory");
                }
                for (i = 0; i < num_text; i++) {
                    if (text_ptr[i].key) {
                        out->text_keys[i] = dup_or_null(text_ptr[i].key);
                    } else {
                        out->text_key_na[i] = 1;
                    }
                    if (text_ptr[i].text) {
                        out->text_vals[i] = dup_or_null(text_ptr[i].text);
                    } else {
                        out->text_val_na[i] = 1;
                    }
                }
            }
#endif
        }

#if !defined(__BIG_ENDIAN__) && !defined(__LITTLE_ENDIAN__)
        {
            char bo[4] = {1, 0, 0, 0};
            int bi;
            memcpy(&bi, bo, 4);
            if (bi != 1)
                need_swap = 1;
        }
#endif
#ifdef __BIG_ENDIAN__
        need_swap = 1;
#endif

        if (color_type == PNG_COLOR_TYPE_PALETTE)
            png_set_palette_to_rgb(png_ptr);
        if (color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)
            png_set_expand_gray_1_2_4_to_8(png_ptr);
        if (bit_depth < 8)
            png_set_packing(png_ptr);
        if (png_get_valid(png_ptr, info_ptr, PNG_INFO_tRNS))
            png_set_tRNS_to_alpha(png_ptr);
        if (bit_depth == 16 && native) {
            add_warning(&rj, "Image uses 16-bit channels but R native format only supports 8-bit, truncating LSB.\n");
            png_set_strip_16(png_ptr);
        }
        if (native) {
            if (color_type == PNG_COLOR_TYPE_GRAY || color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
                png_set_gray_to_rgb(png_ptr);
            if (!(color_type & PNG_COLOR_MASK_ALPHA))
                png_set_add_alpha(png_ptr, 0xFF, PNG_FILLER_AFTER);
        }
        png_set_interlace_handling(png_ptr);
        png_read_update_info(png_ptr, info_ptr);
        rowbytes = (int)png_get_rowbytes(png_ptr, info_ptr);
        bit_depth = png_get_bit_depth(png_ptr, info_ptr);
        color_type = png_get_color_type(png_ptr, info_ptr);

        if (height > 0 && rowbytes > 0) {
            row_pointers = (png_bytepp)malloc((size_t)height * sizeof(png_bytep));
            img_memory = (unsigned char *)malloc((size_t)height * (size_t)rowbytes);
            rj.rows = row_pointers;
            rj.image = img_memory;
            if (!row_pointers || !img_memory) {
                free(row_pointers);
                free(img_memory);
                rj.rows = NULL;
                rj.image = NULL;
                png_error(png_ptr, "out of memory");
            }
            for (y = 0; y < (int)height; y++)
                row_pointers[y] = img_memory + (size_t)y * (size_t)rowbytes;
            png_read_image(png_ptr, row_pointers);
        } else {
            row_pointers = NULL;
            img_memory = NULL;
        }

        if (rj.f) {
            fclose(rj.f);
            rj.f = NULL;
        }

        out->height = (int)height;
        out->width = (int)width;
        out->native_mode = native ? 1 : 0;

        if (native) {
            int pln = width == 0 ? 0 : rowbytes / (int)width;
            int x;
            int32_t *idata;
            if (pln < 1 || pln > 4) {
                free(row_pointers);
                free(img_memory);
                rj.rows = NULL;
                rj.image = NULL;
                snprintf(out->error, sizeof out->error, "native output for %d planes is not possible.", pln);
                png_destroy_read_struct(&png_ptr, &info_ptr, NULL);
                readpng_free(out);
                return 0;
            }
            out->channels = pln;
            out->n_samples = (int)(width * height);
            out->native_pixels = (int *)malloc((size_t)out->n_samples * sizeof(int));
            if (!out->native_pixels && out->n_samples) {
                free(row_pointers);
                free(img_memory);
                rj.rows = NULL;
                rj.image = NULL;
                png_error(png_ptr, "out of memory");
            }
            idata = (int32_t *)out->native_pixels;
            if (pln == 4) {
                for (y = 0; y < (int)height; y++)
                    memcpy(idata + (size_t)y * width, row_pointers[y], (size_t)width * sizeof(int));
                if (need_swap) {
                    int n = out->n_samples;
                    int i;
                    for (i = 0; i < n; i++) {
                        unsigned int value = (unsigned int)idata[i];
                        RX_swap32(value);
                        idata[i] = (int32_t)value;
                    }
                }
            } else if (pln == 3) {
                for (y = 0; y < (int)height; y++)
                    for (x = 0; x < rowbytes; x += 3)
                        *(idata++) = (int32_t)R_RGB(row_pointers[y][x], row_pointers[y][x + 1], row_pointers[y][x + 2]);
            } else if (pln == 2) {
                for (y = 0; y < (int)height; y++)
                    for (x = 0; x < rowbytes; x += 2)
                        *(idata++) = (int32_t)R_RGBA(row_pointers[y][x], row_pointers[y][x], row_pointers[y][x], row_pointers[y][x + 1]);
            } else {
                for (y = 0; y < (int)height; y++)
                    for (x = 0; x < rowbytes; x++)
                        *(idata++) = (int32_t)R_RGB(row_pointers[y][x], row_pointers[y][x], row_pointers[y][x]);
            }
        } else {
            int x, p, pln, pls;
            double *data;
            pln = width == 0 ? 0 : rowbytes / (int)width;
            pls = (int)(width * height);
            if (bit_depth == 16) {
                out->n_samples = rowbytes * (int)height / 2;
                pln /= 2;
            } else {
                out->n_samples = rowbytes * (int)height;
            }
            out->planes = pln;
            out->samples = (double *)malloc((size_t)(out->n_samples > 0 ? out->n_samples : 1) * sizeof(double));
            if (!out->samples) {
                free(row_pointers);
                free(img_memory);
                rj.rows = NULL;
                rj.image = NULL;
                png_error(png_ptr, "out of memory");
            }
            data = out->samples;
            if (bit_depth == 16) {
                for (y = 0; y < (int)height; y++)
                    for (x = 0; x < (int)width; x++)
                        for (p = 0; p < pln; p++) {
                            unsigned int hi = img_memory ? row_pointers[y][2 * (x * pln + p)] : 0;
                            unsigned int lo = img_memory ? row_pointers[y][2 * (x * pln + p) + 1] : 0;
                            data[y + x * (int)height + p * pls] = (double)((hi << 8) | lo) / 65535.0;
                        }
            } else {
                for (y = 0; y < (int)height; y++)
                    for (x = 0; x < (int)width; x++)
                        for (p = 0; p < pln; p++)
                            data[y + x * (int)height + p * pls] = (double)row_pointers[y][x * pln + p] / 255.0;
            }
        }
        free(row_pointers);
        free(img_memory);
        rj.rows = NULL;
        rj.image = NULL;
    }

    if (rj.warning_used)
        snprintf(out->warning, sizeof out->warning, "%s", rj.warning);
    png_destroy_read_struct(&png_ptr, &info_ptr, NULL);
    out->ok = 1;
    return 1;
}
