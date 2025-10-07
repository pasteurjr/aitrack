import L from 'leaflet';

// SVG base do ícone do carro. A cor será trocada via `style`.
const carSvg = `
<svg fill="#COLOR#" version="1.1" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	 viewBox="0 0 30.051 30.051" xml:space="preserve">
<g>
	<path d="M26.031,10.213c-0.206-0.259-0.533-0.38-0.848-0.313l-3.24,0.692V6.865c0-3.452-2.804-6.256-6.256-6.256h-3.32
		c-3.452,0-6.256,2.804-6.256,6.256v3.727l-3.24-0.692c-0.315-0.067-0.642,0.054-0.848,0.313c-0.206,0.259-0.259,0.602-0.149,0.91
		l1.983,5.593c0.148,0.418,0.549,0.698,0.996,0.698h1.983v2.644c0,1.764,1.433,3.197,3.197,3.197h0.732v1.66
		c0,0.553,0.448,1,1,1h6.64c0.553,0,1-0.447,1-1v-1.66h0.732c1.764,0,3.197-1.433,3.197-3.197v-2.644h1.983
		c0.447,0,0.848-0.28,0.996-0.698l1.983-5.593C26.29,10.815,26.237,10.472,26.031,10.213z M9.375,6.865
		c0-2.28,1.853-4.13,4.13-4.13h3.32c2.277,0,4.13,1.85,4.13,4.13v3.02H9.375V6.865z M20.955,19.918c0,0.6-0.486,1.088-1.088,1.088
		h-9.668c-0.601,0-1.088-0.487-1.088-1.088v-2.644h11.843V19.918z"/>
</g>
</svg>
`;

const createVehicleIcon = (color: string) => {
    return L.divIcon({
        html: carSvg.replace('#COLOR#', color),
        className: '', // para não adicionar estilos padrão do leaflet
        iconSize: [35, 35],
        iconAnchor: [17, 35],
        popupAnchor: [0, -35]
    });
}

// Ícone para veículo em movimento (Verde)
export const movingIcon = createVehicleIcon('#28a745');

// Ícone para veículo parado (Vermelho)
export const stoppedIcon = createVehicleIcon('#dc3545');
