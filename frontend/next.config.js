/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
    // Explicitly allow placeholder image domains
    domains: ['picsum.photos', 'images.unsplash.com'],
  },
}

module.exports = nextConfig
