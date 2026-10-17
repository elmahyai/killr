/* writePNG's libpng calls, loaded with ctypes.

libpng reports errors with longjmp. The setjmp stays in this function so
Python callbacks never catch the jump.
*/

#include <png.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INIT_SIZE (1024 * 256)
#define R_RED(v) ((unsigned char)((v) & 0xFF))
#define R_GREEN(v) ((unsigned char)(((v) >> 8) & 0xFF))
#define R_BLUE(v) ((unsigned char)(((v) >> 16) & 0xFF))
#define R_ALPHA(v) ((unsigned char)(((v) >> 24) & 0xFF))
#define RX_swap32(X)                                                                               \
    (X) = (((unsigned int)(X)) >> 24) | ((((unsigned int)(X)) >> 8) & 0xff00u) |                   \
           (((unsigned int)(X)) << 24) | ((((unsigned int)(X)) & 0xff00u) << 8)

typedef struct write_job {
    FILE *f;
    int ptr, len;
    unsigned char *data;
    unsigned char **blocks;
    int nblocks;
    int block_cap;
    size_t total;
} write_job_t;

typedef struct writepng_result {
    unsigned char *data;
    size_t length;
    int ok;
    char error[1024];
    char warning[2048];
    size_t warning_used;
} writepng_result;

static void add_warning(write_job_t *rj, const char *text) {
    (void)rj;
    (void)text;
}

static void user_error_fn(png_structp png_ptr, png_const_charp error_msg) {
    write_job_t *rj = (write_job_t *)png_get_error_ptr(png_ptr);
    if (rj && rj->f) {
        fclose(rj->f);
        rj->f = NULL;
    }
    png_longjmp(png_ptr, 1);
}

static void user_warning_fn(png_structp png_ptr, png_const_charp warning_msg) {
    (void)png_ptr;
    (void)warning_msg;
}

static int append_block(write_job_t *rj, size_t size) {
    unsigned char *block;
    if (rj->nblocks >= rj->block_cap) {
        int cap = rj->block_cap ? rj->block_cap * 2 : 4;
        unsigned char **next = (unsigned char **)realloc(rj->blocks, (size_t)cap * sizeof(unsigned char *));
        if (!next)
            return 0;
        rj->blocks = next;
        rj->block_cap = cap;
    }
    block = (unsigned char *)malloc(size);
    if (!block)
        return 0;
    rj->blocks[rj->nblocks++] = block;
    rj->data = block;
    rj->len = (int)size;
    rj->ptr = 0;
    return 1;
}

static void user_write_data(png_structp png_ptr, png_bytep data, png_size_t length) {
    write_job_t *rj = (write_job_t *)png_get_io_ptr(png_ptr);
    png_size_t to_write = length;
    while (length) {
        if (to_write > (png_size_t)(rj->len - rj->ptr))
            to_write = (png_size_t)(rj->len - rj->ptr);
        if (to_write > 0) {
            memcpy(rj->data + rj->ptr, data, to_write);
            rj->ptr += (int)to_write;
            length -= to_write;
            data += to_write;
            rj->total += to_write;
        }
        if (length) {
            if (!append_block(rj, INIT_SIZE))
                png_error(png_ptr, "out of memory");
            to_write = length;
        }
    }
}

static void user_flush_data(png_structp png_ptr) {
    (void)png_ptr;
}

void writepng_free(writepng_result *out) {
    if (!out)
        return;
    free(out->data);
    out->data = NULL;
    out->length = 0;
}

static void fail(writepng_result *out, const char *message) {
    snprintf(out->error, sizeof out->error, "%s", message);
    out->ok = 0;
}

int writepng_write(const double *real_image, const int32_t *native_image, const unsigned char *raw_image,
                   int native, int raw_array, int height, int width, int planes, int channels_attr,
                   const char *path, int to_raw, double dpi_x, double dpi_y, int use_dpi,
                   const char **text_keys, const char **text_vals, int ntext, writepng_result *out) {
    write_job_t rj;
    png_structp png_ptr;
    png_infop info_ptr;
    volatile FILE *file = NULL;
    volatile png_structp png_volatile = NULL;
    volatile png_infop info_volatile = NULL;
    int rowbytes;
    png_bytepp row_pointers = NULL;
    png_bytep flat_rows = NULL;
    int y;

    memset(out, 0, sizeof *out);
    memset(&rj, 0, sizeof rj);

    if (native && raw_array)
        native = 1;

    if (!native && !raw_array && !real_image) {
        fail(out, "image must be a matrix or array of raw or real numbers");
        return 0;
    }

    if (planes < 1 || planes > 4) {
        fail(out, "image must have either 1 (grayscale), 2 (GA), 3 (RGB) or 4 (RGBA) planes");
        return 0;
    }

    if (native && planes > 1 && !raw_array) {
        fail(out, "native raster must be a matrix");
        return 0;
    }

    if (native) {
        if (channels_attr >= 1 && channels_attr <= 4)
            planes = channels_attr;
        else if (!raw_array)
            planes = 4;
    }

    if (raw_array) {
        if (planes != 4) {
            fail(out, "Only RGBA format is supported as raw data");
            return 0;
        }
        native = 1;
    }

    if (to_raw) {
        if (!append_block(&rj, INIT_SIZE)) {
            fail(out, "out of memory");
            return 0;
        }
        rj.f = NULL;
    } else {
        FILE *opened;
        if (!path || !path[0]) {
            fail(out, "invalid filename");
            return 0;
        }
        opened = fopen(path, "wb");
        if (!opened) {
            snprintf(out->error, sizeof out->error, "unable to create %s", path);
            return 0;
        }
        file = opened;
        rj.f = opened;
    }

    png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, &rj, user_error_fn, user_warning_fn);
    if (!png_ptr) {
        if (file)
            fclose((FILE *)file);
        free(rj.blocks ? rj.blocks[0] : NULL);
        free(rj.blocks);
        fail(out, "unable to initialize libpng");
        return 0;
    }
    png_volatile = png_ptr;

    info_ptr = png_create_info_struct(png_ptr);
    if (!info_ptr) {
        if (file)
            fclose((FILE *)file);
        png_destroy_write_struct(&png_ptr, NULL);
        for (y = 0; y < rj.nblocks; y++)
            free(rj.blocks[y]);
        free(rj.blocks);
        fail(out, "unable to initialize libpng");
        return 0;
    }
    info_volatile = info_ptr;

    if (setjmp(png_jmpbuf(png_ptr))) {
        png_structp dead = (png_structp)png_volatile;
        png_infop dead_info = (png_infop)info_volatile;
        free(row_pointers);
        free(flat_rows);
        if (dead)
            png_destroy_write_struct(&dead, dead_info ? &dead_info : NULL);
        if (file && rj.f) {
            fclose(rj.f);
            rj.f = NULL;
        }
        for (y = 0; y < rj.nblocks; y++)
            free(rj.blocks[y]);
        free(rj.blocks);
        if (!out->error[0])
            fail(out, "libpng error: ");
        return 0;
    }

    if (rj.f)
        png_init_io(png_ptr, rj.f);
    else
        png_set_write_fn(png_ptr, &rj, user_write_data, user_flush_data);

    png_set_IHDR(png_ptr, info_ptr, (png_uint_32)width, (png_uint_32)height, 8,
                 (planes == 1) ? PNG_COLOR_TYPE_GRAY
                 : (planes == 2) ? PNG_COLOR_TYPE_GRAY_ALPHA
                 : (planes == 3) ? PNG_COLOR_TYPE_RGB
                                 : PNG_COLOR_TYPE_RGB_ALPHA,
                 PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);

#ifdef PNG_pHYs_SUPPORTED
    if (use_dpi == 1)
        png_set_pHYs(png_ptr, info_ptr, (png_uint_32)(dpi_x * 39.37008 + 0.5),
                     (png_uint_32)(dpi_y * 39.37008 + 0.5), PNG_RESOLUTION_METER);
    else if (use_dpi == 2)
        png_set_pHYs(png_ptr, info_ptr, (png_uint_32)(dpi_x * 10000.0 + 0.5),
                     (png_uint_32)(dpi_y * 10000.0 + 0.5), PNG_RESOLUTION_UNKNOWN);
#endif

    if (ntext > 0 && text_keys && text_vals) {
        png_text *text_ptr = (png_text *)calloc((size_t)ntext, sizeof(png_text));
        int i;
        if (!text_ptr)
            png_error(png_ptr, "out of memory");
        for (i = 0; i < ntext; i++) {
            text_ptr[i].compression = PNG_TEXT_COMPRESSION_NONE;
            text_ptr[i].key = (char *)(text_keys[i] ? text_keys[i] : "");
            text_ptr[i].text = (char *)(text_vals[i] ? text_vals[i] : "");
        }
        png_set_text(png_ptr, info_ptr, text_ptr, ntext);
        free(text_ptr);
    }

    rowbytes = width * planes;
    row_pointers = (png_bytepp)malloc((size_t)height * sizeof(png_bytep));
    flat_rows = (png_bytep)malloc((size_t)height * (size_t)rowbytes);
    if (!row_pointers || !flat_rows)
        png_error(png_ptr, "out of memory");
    for (y = 0; y < height; y++)
        row_pointers[y] = flat_rows + (size_t)y * (size_t)rowbytes;

    if (!native) {
        int x, p, pls = width * height;
        for (y = 0; y < height; y++)
            for (x = 0; x < width; x++)
                for (p = 0; p < planes; p++) {
                    double v = real_image[y + x * height + p * pls];
                    if (v < 0)
                        v = 0;
                    if (v > 255.0)
                        v = 1.0;
                    row_pointers[y][x * planes + p] = (unsigned char)(v * 255.0 + 0.5);
                }
    } else if (planes == 4) {
        const int32_t *idata = raw_array ? (const int32_t *)raw_image : native_image;
        int need_swap = 0;
        for (y = 0; y < height; y++)
            memcpy(row_pointers[y], idata + (size_t)y * (size_t)width, (size_t)width * sizeof(int32_t));
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
        if (need_swap) {
            unsigned int *idp = (unsigned int *)flat_rows;
            unsigned int *ide = idp + (size_t)height * (size_t)width;
            for (; idp < ide; idp++)
                RX_swap32(*idp);
        }
    } else {
        const int32_t *idata = native_image;
        int x;
        for (y = 0; y < height; y++)
            for (x = 0; x < rowbytes; idata++) {
                if (planes == 3) {
                    row_pointers[y][x++] = R_RED(*idata);
                    row_pointers[y][x++] = R_GREEN(*idata);
                    row_pointers[y][x++] = R_BLUE(*idata);
                } else if (planes == 2) {
                    row_pointers[y][x++] = R_RED(*idata);
                    row_pointers[y][x++] = R_ALPHA(*idata);
                } else {
                    row_pointers[y][x++] = R_RED(*idata);
                }
            }
    }

    png_set_rows(png_ptr, info_ptr, row_pointers);
    png_write_png(png_ptr, info_ptr, PNG_TRANSFORM_IDENTITY, NULL);
    png_destroy_write_struct(&png_ptr, &info_ptr);
    png_volatile = NULL;
    info_volatile = NULL;

    free(row_pointers);
    free(flat_rows);

    if (rj.f) {
        fclose(rj.f);
        rj.f = NULL;
        for (y = 0; y < rj.nblocks; y++)
            free(rj.blocks[y]);
        free(rj.blocks);
        out->ok = 1;
        return 1;
    }

    out->length = rj.total;
    out->data = (unsigned char *)malloc(out->length ? out->length : 1);
    if (!out->data) {
        for (y = 0; y < rj.nblocks; y++)
            free(rj.blocks[y]);
        free(rj.blocks);
        fail(out, "out of memory");
        return 0;
    }
    {
        size_t to_go = out->length;
        unsigned char *dest = out->data;
        int i;
        for (i = 0; i < rj.nblocks && to_go; i++) {
            size_t chunk = (size_t)rj.len;
            if (chunk > to_go)
                chunk = to_go;
            memcpy(dest, rj.blocks[i], chunk);
            dest += chunk;
            to_go -= chunk;
        }
    }
    for (y = 0; y < rj.nblocks; y++)
        free(rj.blocks[y]);
    free(rj.blocks);
    out->ok = 1;
    return 1;
}
