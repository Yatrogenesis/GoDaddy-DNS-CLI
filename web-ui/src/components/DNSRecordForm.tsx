import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X } from 'lucide-react';
import type { DNSRecord, CreateRecordRequest } from '@/types/api';

const dnsRecordSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  type: z.enum(['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'SRV', 'NS', 'CAA']),
  data: z.string().min(1, 'Data is required'),
  ttl: z.number().min(300, 'TTL must be at least 300 seconds').max(86400, 'TTL must be at most 86400 seconds'),
  priority: z.number().optional(),
});

type DNSRecordFormData = z.infer<typeof dnsRecordSchema>;

interface DNSRecordFormProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateRecordRequest) => void;
  editRecord?: DNSRecord;
  domain: string;
}

const recordTypeDescriptions: Record<string, string> = {
  A: 'IPv4 address (e.g., 192.168.1.1)',
  AAAA: 'IPv6 address (e.g., 2001:db8::1)',
  CNAME: 'Canonical name (e.g., www.example.com)',
  MX: 'Mail exchange (e.g., mail.example.com)',
  TXT: 'Text record (e.g., "v=spf1 include:_spf.google.com ~all")',
  SRV: 'Service record (e.g., _service._protocol)',
  NS: 'Name server (e.g., ns1.example.com)',
  CAA: 'Certificate Authority Authorization',
};

export const DNSRecordForm: React.FC<DNSRecordFormProps> = ({
  isOpen,
  onClose,
  onSubmit,
  editRecord,
  domain,
}) => {
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DNSRecordFormData>({
    resolver: zodResolver(dnsRecordSchema),
    defaultValues: editRecord ? {
      name: editRecord.name,
      type: editRecord.type as any,
      data: editRecord.data,
      ttl: editRecord.ttl,
      priority: editRecord.priority,
    } : {
      name: '',
      type: 'A',
      data: '',
      ttl: 3600,
    },
  });

  const selectedType = watch('type');
  const requiresPriority = selectedType === 'MX' || selectedType === 'SRV';

  React.useEffect(() => {
    if (editRecord) {
      reset({
        name: editRecord.name,
        type: editRecord.type as any,
        data: editRecord.data,
        ttl: editRecord.ttl,
        priority: editRecord.priority,
      });
    } else {
      reset({
        name: '',
        type: 'A',
        data: '',
        ttl: 3600,
      });
    }
  }, [editRecord, reset]);

  const handleFormSubmit = (data: DNSRecordFormData) => {
    onSubmit({
      name: data.name,
      type: data.type,
      data: data.data,
      ttl: data.ttl,
      priority: requiresPriority ? data.priority : undefined,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-lg bg-white rounded-lg shadow-lg">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            {editRecord ? 'Edit DNS Record' : 'Add DNS Record'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Domain
            </label>
            <div className="text-sm text-gray-500 bg-gray-50 p-2 rounded">
              {domain}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              {...register('name')}
              placeholder="@ for root domain, www for subdomain"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.name && (
              <p className="text-red-600 text-sm mt-1">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              {...register('type')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(recordTypeDescriptions).map(([type, description]) => (
                <option key={type} value={type}>
                  {type} - {description}
                </option>
              ))}
            </select>
            {errors.type && (
              <p className="text-red-600 text-sm mt-1">{errors.type.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Value
            </label>
            <input
              type="text"
              {...register('data')}
              placeholder={recordTypeDescriptions[selectedType]}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.data && (
              <p className="text-red-600 text-sm mt-1">{errors.data.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                TTL (seconds)
              </label>
              <input
                type="number"
                {...register('ttl', { valueAsNumber: true })}
                min="300"
                max="86400"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.ttl && (
                <p className="text-red-600 text-sm mt-1">{errors.ttl.message}</p>
              )}
            </div>

            {requiresPriority && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <input
                  type="number"
                  {...register('priority', { valueAsNumber: true })}
                  min="0"
                  max="65535"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.priority && (
                  <p className="text-red-600 text-sm mt-1">{errors.priority.message}</p>
                )}
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : editRecord ? 'Update Record' : 'Create Record'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};